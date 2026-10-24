"""File persistante de scans sans dépendance à Redis."""

from datetime import UTC, datetime, timedelta
from secrets import randbelow

from sqlalchemy import and_, or_, select, update
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.models.entities import Scan, ScanStatus

MAX_ATTEMPTS = 3
LEASE_DURATION = timedelta(minutes=5)


def _eligible(now: datetime) -> ColumnElement[bool]:
    return or_(
        and_(
            Scan.status == ScanStatus.QUEUED,
            or_(Scan.next_attempt_at.is_(None), Scan.next_attempt_at <= now),
        ),
        and_(Scan.status == ScanStatus.RUNNING, Scan.lease_expires_at < now),
    )


def claim_next_scan(db: Session, worker_id: str, now: datetime | None = None) -> str | None:
    """Acquiert au plus un scan avec une unique instruction UPDATE atomique."""
    claimed_at = now or datetime.now(UTC)
    db.execute(
        update(Scan)
        .where(
            Scan.status == ScanStatus.RUNNING,
            Scan.lease_expires_at < claimed_at,
            Scan.attempt_count >= MAX_ATTEMPTS,
        )
        .values(
            status=ScanStatus.FAILED,
            error_code="worker_interrupted",
            finished_at=claimed_at,
            lease_owner=None,
            lease_expires_at=None,
        )
    )
    candidate = (
        select(Scan.id)
        .where(_eligible(claimed_at), Scan.attempt_count < MAX_ATTEMPTS)
        .order_by(Scan.created_at, Scan.id)
        .limit(1)
        .scalar_subquery()
    )
    statement = (
        update(Scan)
        .where(Scan.id == candidate, _eligible(claimed_at))
        .values(
            status=ScanStatus.RUNNING,
            lease_owner=worker_id,
            lease_expires_at=claimed_at + LEASE_DURATION,
            next_attempt_at=None,
            started_at=claimed_at,
            attempt_count=Scan.attempt_count + 1,
            error_code=None,
        )
        .returning(Scan.id)
    )
    scan_id = db.scalar(statement)
    db.commit()
    return scan_id


def schedule_retry(
    db: Session,
    scan_id: str,
    now: datetime | None = None,
    *,
    jitter_seconds: float | None = None,
) -> None:
    failed_at = now or datetime.now(UTC)
    scan = db.get(Scan, scan_id)
    if scan is None or scan.status == ScanStatus.CANCELLED:
        return
    scan.lease_owner = None
    scan.lease_expires_at = None
    if scan.attempt_count >= MAX_ATTEMPTS:
        scan.status = ScanStatus.FAILED
        scan.error_code = "connector_error"
        scan.finished_at = failed_at
    else:
        scan.status = ScanStatus.QUEUED
        scan.error_code = "retry_scheduled"
        jitter = randbelow(1001) / 1000 if jitter_seconds is None else jitter_seconds
        scan.next_attempt_at = failed_at + timedelta(seconds=2**scan.attempt_count + jitter)
    db.commit()
