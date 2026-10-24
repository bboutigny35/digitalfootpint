"""Transformation atomique des échéances en scans persistants."""

import calendar
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.entities import Scan, ScanSchedule


def _as_utc(value: datetime) -> datetime:
    """Normalise les dates SQLite sans fuseau avant toute comparaison Python."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def next_occurrence(value: datetime, cadence: str) -> datetime:
    if cadence == "daily":
        return value + timedelta(days=1)
    if cadence == "weekly":
        return value + timedelta(days=7)
    if cadence == "monthly":
        year = value.year + (1 if value.month == 12 else 0)
        month = 1 if value.month == 12 else value.month + 1
        day = min(value.day, calendar.monthrange(year, month)[1])
        return value.replace(year=year, month=month, day=day)
    raise ValueError("Cadence inconnue")


def enqueue_due_schedules(
    db: Session, now: datetime | None = None, *, max_schedules: int = 50
) -> int:
    due_at = _as_utc(now) if now is not None else datetime.now(UTC)
    created = 0
    for _ in range(max_schedules):
        candidate = (
            select(ScanSchedule.id)
            .where(ScanSchedule.enabled.is_(True), ScanSchedule.next_run_at <= due_at)
            .order_by(ScanSchedule.next_run_at, ScanSchedule.id)
            .limit(1)
            .scalar_subquery()
        )
        schedule = db.scalar(
            update(ScanSchedule)
            .where(
                ScanSchedule.id == candidate,
                ScanSchedule.enabled.is_(True),
                ScanSchedule.next_run_at <= due_at,
            )
            .values(last_run_at=due_at)
            .returning(ScanSchedule)
        )
        if schedule is None:
            db.commit()
            break
        next_run_at = next_occurrence(_as_utc(schedule.next_run_at), schedule.cadence)
        while next_run_at <= due_at:
            next_run_at = next_occurrence(next_run_at, schedule.cadence)
        schedule.next_run_at = next_run_at
        db.add(
            Scan(
                owner_id=schedule.owner_id,
                profile_id=schedule.profile_id,
                connector_ids=list(schedule.connector_ids),
            )
        )
        db.commit()
        created += 1
    return created
