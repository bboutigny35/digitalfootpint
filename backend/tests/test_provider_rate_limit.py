import asyncio
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.entities import ProviderThrottle
from app.workers.rate_limit import defer_provider_until, reserve_request_slot, wait_for_request_slot


def test_provider_slots_are_persisted_and_shared(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'rate-limit.db'}")
    Base.metadata.create_all(engine)
    now = datetime.now(UTC).replace(tzinfo=None)
    with Session(engine) as first:
        assert reserve_request_slot(first, "github", 10, now) == now
    with Session(engine) as second:
        assert reserve_request_slot(second, "github", 10, now) == now + timedelta(seconds=6)
        next_window = now + timedelta(seconds=6)
        assert reserve_request_slot(second, "github", 10, next_window) == next_window


def test_provider_rate_must_be_positive(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'rate-invalid.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db, pytest.raises(ValueError, match="positive"):
        reserve_request_slot(db, "github", 0)


def test_provider_can_be_deferred_until_remote_quota_reset(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'quota.db'}")
    Base.metadata.create_all(engine)
    now = datetime.now(UTC).replace(tzinfo=None)
    reset_at = now + timedelta(hours=1)
    with Session(engine) as db:
        defer_provider_until(db, "github", reset_at)
        assert reserve_request_slot(db, "github", 10, now) == reset_at
        throttle = db.get(ProviderThrottle, "github")
        assert throttle is not None
        assert throttle.next_request_at == reset_at


def test_wait_for_slot_interrupts_a_rate_limit_wait_on_shutdown(monkeypatch) -> None:
    shutdown = False
    sleep_durations: list[float] = []

    async def request_shutdown_after_poll(seconds: float) -> None:
        nonlocal shutdown
        sleep_durations.append(seconds)
        shutdown = True

    monkeypatch.setattr("app.workers.rate_limit.SessionLocal", lambda: nullcontext(None))
    monkeypatch.setattr(
        "app.workers.rate_limit.reserve_request_slot",
        lambda db, connector_id, rate, now: now + timedelta(seconds=60),
    )
    monkeypatch.setattr(asyncio, "sleep", request_shutdown_after_poll)
    with pytest.raises(asyncio.CancelledError, match="Arrêt du worker"):
        asyncio.run(
            wait_for_request_slot("github", 10, should_stop=lambda: shutdown)
        )
    assert sleep_durations == [0.25]
