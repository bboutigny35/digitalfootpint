"""Finalisation honnête des contrôles de plateformes d'une campagne."""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.entities import PlatformCatalogEntry, PlatformCheckResult, Result, Scan

INHERENTLY_NON_PUBLIC_METHODS = ("none", "user_verification")


@dataclass(frozen=True, slots=True)
class PlatformCheckSummary:
    evaluated_count: int
    public_match_count: int
    not_verifiable_count: int


def finalize_platform_checks(
    db: Session,
    scan: Scan,
    *,
    now: datetime | None = None,
    commit: bool = True,
) -> PlatformCheckSummary:
    checked_at = now or datetime.now(UTC)
    selected_connectors = set(scan.connector_ids)
    result_counts = {
        connector_id: count
        for connector_id, count in db.execute(
            select(Result.connector_id, func.count(Result.id))
            .where(Result.scan_id == scan.id)
            .group_by(Result.connector_id)
        )
    }
    catalog = list(
        db.scalars(
            select(PlatformCatalogEntry)
            .where(
                or_(
                    PlatformCatalogEntry.connector_id.in_(selected_connectors),
                    PlatformCatalogEntry.verification_method.in_(INHERENTLY_NON_PUBLIC_METHODS),
                )
            )
            .order_by(PlatformCatalogEntry.priority, PlatformCatalogEntry.identifier)
        )
    )
    public_match_count = 0
    not_verifiable_count = 0
    for platform in catalog:
        connector_was_run = bool(
            platform.connector_id and platform.connector_id in selected_connectors
        )
        count = result_counts.get(platform.connector_id or "", 0) if connector_was_run else 0
        if connector_was_run:
            status = "PUBLIC_MATCH" if count else "NO_PUBLIC_RESULT"
            public_match_count += int(bool(count))
        else:
            status = "NOT_VERIFIABLE"
            not_verifiable_count += 1
        stored = db.scalar(
            select(PlatformCheckResult).where(
                PlatformCheckResult.scan_id == scan.id,
                PlatformCheckResult.platform_identifier == platform.identifier,
            )
        )
        if stored is None:
            stored = PlatformCheckResult(
                owner_id=scan.owner_id,
                scan_id=scan.id,
                platform_identifier=platform.identifier,
            )
            db.add(stored)
        stored.connector_id = platform.connector_id
        stored.verification_method = platform.verification_method
        stored.status = status
        stored.result_count = count
        stored.error_code = None
        stored.checked_at = checked_at
        platform.last_checked_at = checked_at
        platform.last_error_code = None
    if commit:
        db.commit()
    else:
        db.flush()
    return PlatformCheckSummary(
        evaluated_count=len(catalog),
        public_match_count=public_match_count,
        not_verifiable_count=not_verifiable_count,
    )
