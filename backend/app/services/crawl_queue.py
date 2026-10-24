import hashlib
import ipaddress
from dataclasses import dataclass
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import CrawlJob, CrawlStatistics, DiscoveredURL, Scan
from app.services.normalization import canonicalize_url

MAX_DEPTH = 5


@dataclass(frozen=True, slots=True)
class EnqueueResult:
    discovered_url: DiscoveredURL
    crawl_job: CrawlJob
    created: bool


def _validate_queue_url(url: str) -> tuple[str, str]:
    raw = urlsplit(url.strip())
    if raw.username is not None or raw.password is not None:
        raise ValueError("Identifiants intégrés à l'URL interdits")
    canonical = canonicalize_url(url)
    parsed = urlsplit(canonical)
    if parsed.port not in {None, 80, 443}:
        raise ValueError("Port sortant interdit")
    assert parsed.hostname is not None
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        pass
    else:
        if not address.is_global:
            raise ValueError("Destination réseau non publique interdite")
    return canonical, parsed.hostname.casefold().rstrip(".")


def enqueue_discovered_url(
    db: Session,
    scan: Scan,
    url: str,
    *,
    source_id: str | None = None,
    discovery_method: str,
    depth: int = 0,
    priority: int = 100,
) -> EnqueueResult:
    if not 0 <= depth <= MAX_DEPTH:
        raise ValueError("Profondeur de crawl invalide")
    if not 1 <= priority <= 1000:
        raise ValueError("Priorité de crawl invalide")
    canonical, domain = _validate_queue_url(url)
    url_hash = hashlib.sha256(canonical.encode()).hexdigest()
    existing = db.scalar(
        select(DiscoveredURL).where(
            DiscoveredURL.scan_id == scan.id, DiscoveredURL.url_hash == url_hash
        )
    )
    if existing is not None:
        job = db.scalar(select(CrawlJob).where(CrawlJob.discovered_url_id == existing.id))
        assert job is not None
        return EnqueueResult(existing, job, False)

    discovered = DiscoveredURL(
        owner_id=scan.owner_id,
        scan_id=scan.id,
        source_id=source_id,
        original_url=url,
        canonical_url=canonical,
        url_hash=url_hash,
        domain=domain,
        discovery_method=discovery_method,
        depth=depth,
        priority=priority,
    )
    db.add(discovered)
    db.flush()
    job = CrawlJob(
        owner_id=scan.owner_id,
        scan_id=scan.id,
        discovered_url_id=discovered.id,
        priority=priority,
    )
    db.add(job)
    statistics = db.get(CrawlStatistics, scan.id)
    if statistics is None:
        statistics = CrawlStatistics(
            scan_id=scan.id,
            discovered_count=0,
            queued_count=0,
            fetched_count=0,
            failed_count=0,
            bytes_downloaded=0,
        )
        db.add(statistics)
    statistics.discovered_count += 1
    statistics.queued_count += 1
    db.commit()
    db.refresh(discovered)
    db.refresh(job)
    return EnqueueResult(discovered, job, True)
