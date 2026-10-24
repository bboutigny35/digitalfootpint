"""Réservation atomique et persistante des créneaux fournisseur."""

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.entities import ProviderThrottle


def reserve_request_slot(
    db: Session,
    connector_id: str,
    requests_per_minute: int,
    now: datetime | None = None,
) -> datetime:
    if requests_per_minute < 1:
        raise ValueError("La limite doit être positive")
    reserved_at = now or datetime.now(UTC)
    values = {
        "connector_id": connector_id,
        "next_request_at": None,
        "updated_at": reserved_at,
    }
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        statement = postgresql_insert(ProviderThrottle).values(**values)
        db.execute(statement.on_conflict_do_nothing(index_elements=["connector_id"]))
    elif dialect == "sqlite":
        sqlite_statement = sqlite_insert(ProviderThrottle).values(**values)
        db.execute(sqlite_statement.on_conflict_do_nothing(index_elements=["connector_id"]))
    else:
        raise ValueError(f"Moteur non pris en charge pour le rate limiting: {dialect}")

    interval = timedelta(seconds=60 / requests_per_minute)
    acquired = db.scalar(
        update(ProviderThrottle)
        .where(
            ProviderThrottle.connector_id == connector_id,
            or_(
                ProviderThrottle.next_request_at.is_(None),
                ProviderThrottle.next_request_at <= reserved_at,
            ),
        )
        .values(next_request_at=reserved_at + interval, updated_at=reserved_at)
        .returning(ProviderThrottle.next_request_at)
    )
    if acquired is not None:
        db.commit()
        return reserved_at
    available_at = db.scalar(
        select(ProviderThrottle.next_request_at).where(
            ProviderThrottle.connector_id == connector_id
        )
    )
    db.commit()
    if available_at is None:
        raise RuntimeError("État de rate limiting incohérent")
    return available_at


def defer_provider_until(db: Session, connector_id: str, resume_at: datetime) -> None:
    current = db.get(ProviderThrottle, connector_id)
    if current is None:
        current = ProviderThrottle(connector_id=connector_id, next_request_at=resume_at)
        db.add(current)
    elif current.next_request_at is None or _timestamp(current.next_request_at) < _timestamp(
        resume_at
    ):
        current.next_request_at = resume_at
    db.commit()


def _timestamp(value: datetime) -> float:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.timestamp()


async def wait_for_request_slot(
    connector_id: str,
    requests_per_minute: int,
    *,
    should_stop: Callable[[], bool] | None = None,
) -> None:
    while True:
        if should_stop is not None and should_stop():
            raise asyncio.CancelledError("Arrêt du worker demandé")
        now = datetime.now(UTC)
        with SessionLocal() as db:
            available_at = reserve_request_slot(db, connector_id, requests_per_minute, now)
        if available_at.tzinfo is None:
            now = now.replace(tzinfo=None)
        if available_at <= now:
            return
        wait_seconds = max((available_at - now).total_seconds(), 0.01)
        await asyncio.sleep(min(wait_seconds, 0.25 if should_stop is not None else wait_seconds))
