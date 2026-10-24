from datetime import UTC, datetime
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.base import IdentitySnapshot
from app.connectors.registry import ConnectorRegistry
from app.models.entities import IdentityProfile, Result, Scan, ScanStatus
from app.services.correlation import score_signals
from app.services.normalization import canonicalize_url
from app.services.notifications import create_new_mention_notification


def _is_cancelled(scan: Scan) -> bool:
    return scan.status == ScanStatus.CANCELLED


class ScanRunner:
    def __init__(self, registry: ConnectorRegistry) -> None:
        self.registry = registry

    async def run(self, scan_id: str, db: Session) -> None:
        scan = db.scalar(select(Scan).where(Scan.id == scan_id))
        if scan is None:
            raise LookupError("Scan introuvable")
        if scan.status not in {ScanStatus.QUEUED, ScanStatus.RUNNING}:
            return
        profile = db.get(IdentityProfile, scan.profile_id)
        if profile is None:
            scan.status = ScanStatus.FAILED
            scan.error_code = "profile_missing"
            db.commit()
            return
        if scan.status == ScanStatus.QUEUED:
            scan.status = ScanStatus.RUNNING
            scan.started_at = datetime.now(UTC)
        db.commit()
        identity = IdentitySnapshot(
            first_name=profile.first_name,
            last_name=profile.last_name,
            name_variants=tuple(profile.name_variants),
            pseudonyms=tuple(profile.pseudonyms),
            former_pseudonyms=tuple(profile.former_pseudonyms),
            emails=tuple(profile.emails),
            phone_numbers=tuple(profile.phone_numbers),
            city_region=profile.city_region,
            profession=profile.profession,
            employers=tuple(profile.employers),
            domains=tuple(profile.domains),
            keywords=tuple(profile.keywords),
            websites=tuple(profile.websites),
            confirmed_profiles=tuple(profile.confirmed_profiles),
            exact_phrases=tuple(profile.exact_phrases),
            exclusions=tuple(profile.exclusions),
        )
        try:
            for position, connector_id in enumerate(scan.connector_ids, start=1):
                db.refresh(scan)
                if _is_cancelled(scan):
                    return
                connector = self.registry.get(connector_id)
                candidates = await connector.search(identity)
                db.refresh(scan)
                if _is_cancelled(scan):
                    return
                for candidate in candidates:
                    canonical_url = canonicalize_url(candidate.url)
                    exists = db.scalar(
                        select(Result.id).where(
                            Result.scan_id == scan.id,
                            Result.canonical_url == canonical_url,
                        )
                    )
                    if exists:
                        continue
                    score = score_signals(candidate.signals)
                    db.add(
                        Result(
                            owner_id=scan.owner_id,
                            profile_id=profile.id,
                            scan_id=scan.id,
                            connector_id=connector_id,
                            canonical_url=canonical_url,
                            domain=urlsplit(canonical_url).hostname or "",
                            title=candidate.title,
                            snippet=candidate.snippet,
                            match_type=candidate.match_type,
                            relevance_score=score.value,
                            score_explanation=score.explanation,
                        )
                    )
                scan.progress = position / len(scan.connector_ids)
                db.commit()
            db.refresh(scan)
            if _is_cancelled(scan):
                return
            create_new_mention_notification(scan, db)
            scan.status = ScanStatus.COMPLETED
            scan.finished_at = datetime.now(UTC)
            scan.lease_owner = None
            scan.lease_expires_at = None
            db.commit()
        except (LookupError, ValueError):
            db.rollback()
            raise
