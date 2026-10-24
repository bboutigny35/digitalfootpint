import hashlib
import ipaddress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from secrets import randbelow
from urllib.parse import urlsplit

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.orm import Session

from app.models.entities import CrawlJob, CrawlStatistics, DiscoveredURL, Scan
from app.services.normalization import canonicalize_url

MAX_DEPTH = 5
MAX_ATTEMPTS = 3
LEASE_DURATION = timedelta(minutes=5)
MAX_RETRY_AFTER_SECONDS = 86400


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


def claim_next_crawl_job(db: Session, worker_id: str, now: datetime | None = None) -> str | None:
    claimed_at = now or datetime.now(UTC)
    eligible = or_(
        and_(
            CrawlJob.status == "queued",
            or_(CrawlJob.next_attempt_at.is_(None), CrawlJob.next_attempt_at <= claimed_at),
        ),
        and_(CrawlJob.status == "running", CrawlJob.lease_expires_at < claimed_at),
    )
    db.execute(
        update(CrawlJob)
        .where(
            CrawlJob.status == "running",
            CrawlJob.lease_expires_at < claimed_at,
            CrawlJob.attempt_count >= MAX_ATTEMPTS,
        )
        .values(
            status="failed",
            error_code="worker_interrupted",
            finished_at=claimed_at,
            lease_owner=None,
            lease_expires_at=None,
        )
    )
    candidate = (
        select(CrawlJob.id)
        .where(eligible, CrawlJob.attempt_count < MAX_ATTEMPTS)
        .order_by(CrawlJob.priority, CrawlJob.created_at, CrawlJob.id)
        .limit(1)
        .scalar_subquery()
    )
    job_id = db.scalar(
        update(CrawlJob)
        .where(CrawlJob.id == candidate, eligible)
        .values(
            status="running",
            lease_owner=worker_id,
            lease_expires_at=claimed_at + LEASE_DURATION,
            next_attempt_at=None,
            started_at=claimed_at,
            attempt_count=CrawlJob.attempt_count + 1,
            error_code=None,
        )
        .returning(CrawlJob.id)
    )
    db.commit()
    return job_id


def schedule_crawl_retry(
    db: Session,
    job_id: str,
    *,
    error_code: str,
    retry_after_seconds: int | None = None,
    now: datetime | None = None,
    jitter_seconds: float | None = None,
) -> None:
    failed_at = now or datetime.now(UTC)
    job = db.get(CrawlJob, job_id)
    if job is None or job.status in {"cancelled", "paused", "completed"}:
        return
    job.lease_owner = None
    job.lease_expires_at = None
    if job.attempt_count >= MAX_ATTEMPTS:
        job.status = "failed"
        job.error_code = error_code
        job.finished_at = failed_at
        statistics = db.get(CrawlStatistics, job.scan_id)
        if statistics is not None:
            statistics.failed_count += 1
            statistics.queued_count = max(statistics.queued_count - 1, 0)
    else:
        delay = min(max(retry_after_seconds or 2**job.attempt_count, 1), MAX_RETRY_AFTER_SECONDS)
        jitter = randbelow(1001) / 1000 if jitter_seconds is None else jitter_seconds
        job.status = "queued"
        job.error_code = "retry_scheduled"
        job.next_attempt_at = failed_at + timedelta(seconds=delay + jitter)
    db.commit()


def set_scan_crawl_paused(db: Session, scan_id: str, paused: bool) -> int:
    if paused:
        updated_ids = db.scalars(
            update(CrawlJob)
            .where(CrawlJob.scan_id == scan_id, CrawlJob.status == "queued")
            .values(status="paused")
            .returning(CrawlJob.id)
        )
    else:
        updated_ids = db.scalars(
            update(CrawlJob)
            .where(CrawlJob.scan_id == scan_id, CrawlJob.status == "paused")
            .values(status="queued", next_attempt_at=None)
            .returning(CrawlJob.id)
        )
    updated_count = len(updated_ids.all())
    db.commit()
    return updated_count


def crawl_queue_counts(db: Session, scan_id: str) -> dict[str, int]:
    rows = db.execute(
        select(CrawlJob.status, func.count(CrawlJob.id))
        .where(CrawlJob.scan_id == scan_id)
        .group_by(CrawlJob.status)
    )
    return {str(status): count for status, count in rows}
