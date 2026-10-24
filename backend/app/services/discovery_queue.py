"""File persistante des documents de découverte à traiter par campagne."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from secrets import randbelow

from sqlalchemy import and_, or_, select, update
from sqlalchemy.orm import Session

from app.models.entities import DiscoveryJob, Scan, WebSource
from app.services.discovery_documents import (
    DiscoveryBatch,
    DiscoveryEnqueueResult,
    enqueue_discovery_batch,
)

MAX_ATTEMPTS = 3
LEASE_DURATION = timedelta(minutes=5)
MAX_RETRY_AFTER_SECONDS = 86400


@dataclass(frozen=True, slots=True)
class DiscoveryJobEnqueueResult:
    job: DiscoveryJob
    created: bool


def enqueue_source_discovery(
    db: Session,
    scan: Scan,
    source: WebSource,
) -> DiscoveryJobEnqueueResult:
    if source.state != "active":
        raise ValueError("Source Web inactive")
    if source.access_method not in {"sitemap", "feed"}:
        raise ValueError("Méthode de découverte non planifiable")
    existing = db.scalar(
        select(DiscoveryJob).where(
            DiscoveryJob.scan_id == scan.id,
            DiscoveryJob.source_id == source.id,
        )
    )
    if existing is not None:
        return DiscoveryJobEnqueueResult(existing, False)
    job = DiscoveryJob(
        owner_id=scan.owner_id,
        scan_id=scan.id,
        source_id=source.id,
        priority=source.priority,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return DiscoveryJobEnqueueResult(job, True)


def claim_next_discovery_job(
    db: Session,
    worker_id: str,
    now: datetime | None = None,
) -> str | None:
    claimed_at = now or datetime.now(UTC)
    db.execute(
        update(DiscoveryJob)
        .where(
            DiscoveryJob.status == "running",
            DiscoveryJob.lease_expires_at < claimed_at,
            DiscoveryJob.attempt_count >= MAX_ATTEMPTS,
        )
        .values(
            status="failed",
            error_code="worker_interrupted",
            finished_at=claimed_at,
            lease_owner=None,
            lease_expires_at=None,
        )
    )
    eligible = or_(
        and_(
            DiscoveryJob.status == "queued",
            or_(
                DiscoveryJob.next_attempt_at.is_(None),
                DiscoveryJob.next_attempt_at <= claimed_at,
            ),
        ),
        and_(
            DiscoveryJob.status == "running",
            DiscoveryJob.lease_expires_at < claimed_at,
        ),
    )
    candidate = (
        select(DiscoveryJob.id)
        .where(eligible, DiscoveryJob.attempt_count < MAX_ATTEMPTS)
        .order_by(DiscoveryJob.priority, DiscoveryJob.created_at, DiscoveryJob.id)
        .limit(1)
        .scalar_subquery()
    )
    job_id = db.scalar(
        update(DiscoveryJob)
        .where(DiscoveryJob.id == candidate, eligible)
        .values(
            status="running",
            lease_owner=worker_id,
            lease_expires_at=claimed_at + LEASE_DURATION,
            next_attempt_at=None,
            started_at=claimed_at,
            attempt_count=DiscoveryJob.attempt_count + 1,
            error_code=None,
        )
        .returning(DiscoveryJob.id)
    )
    db.commit()
    return job_id


def schedule_discovery_retry(
    db: Session,
    job_id: str,
    *,
    worker_id: str,
    error_code: str,
    retry_after_seconds: int | None = None,
    now: datetime | None = None,
    jitter_seconds: float | None = None,
) -> None:
    failed_at = now or datetime.now(UTC)
    job = db.get(DiscoveryJob, job_id)
    if job is None or not _owns_valid_lease(job, worker_id, failed_at):
        return
    job.lease_owner = None
    job.lease_expires_at = None
    if job.attempt_count >= MAX_ATTEMPTS:
        job.status = "failed"
        job.error_code = error_code
        job.finished_at = failed_at
    else:
        delay = min(max(retry_after_seconds or 2**job.attempt_count, 1), MAX_RETRY_AFTER_SECONDS)
        jitter = randbelow(1001) / 1000 if jitter_seconds is None else jitter_seconds
        job.status = "queued"
        job.error_code = "retry_scheduled"
        job.next_attempt_at = failed_at + timedelta(seconds=delay + jitter)
    db.commit()


def complete_discovery_job(
    db: Session,
    job_id: str,
    *,
    worker_id: str,
    now: datetime | None = None,
) -> None:
    completed_at = now or datetime.now(UTC)
    job = db.get(DiscoveryJob, job_id)
    if job is None or not _owns_valid_lease(job, worker_id, completed_at):
        return
    job.status = "completed"
    job.finished_at = completed_at
    job.lease_owner = None
    job.lease_expires_at = None
    job.error_code = None
    db.commit()


def complete_discovery_with_batch(
    db: Session,
    job_id: str,
    batch: DiscoveryBatch,
    *,
    worker_id: str,
    now: datetime | None = None,
) -> DiscoveryEnqueueResult | None:
    completed_at = now or datetime.now(UTC)
    job = db.get(DiscoveryJob, job_id)
    if job is None or not _owns_valid_lease(job, worker_id, completed_at):
        return None
    scan = db.get(Scan, job.scan_id)
    source = db.get(WebSource, job.source_id)
    if scan is None or source is None:
        raise RuntimeError("État de découverte incomplet")
    result = enqueue_discovery_batch(
        db,
        scan,
        source,
        batch,
        now=completed_at,
        commit=False,
    )
    job.status = "completed"
    job.finished_at = completed_at
    job.lease_owner = None
    job.lease_expires_at = None
    job.error_code = None
    db.commit()
    return result


def fail_discovery_job(
    db: Session,
    job_id: str,
    *,
    worker_id: str,
    error_code: str,
    now: datetime | None = None,
) -> None:
    failed_at = now or datetime.now(UTC)
    job = db.get(DiscoveryJob, job_id)
    if job is None or not _owns_valid_lease(job, worker_id, failed_at):
        return
    job.status = "failed"
    job.finished_at = failed_at
    job.lease_owner = None
    job.lease_expires_at = None
    job.error_code = error_code
    db.commit()


def _owns_valid_lease(job: DiscoveryJob, worker_id: str, now: datetime) -> bool:
    return bool(
        job.status == "running"
        and job.lease_owner == worker_id
        and job.lease_expires_at is not None
        and _timestamp(job.lease_expires_at) > _timestamp(now)
    )


def _timestamp(value: datetime) -> float:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.timestamp()
