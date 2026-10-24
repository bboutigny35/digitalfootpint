from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.entities import IdentityProfile, Scan, ScanStatus, User
from app.security.passwords import hash_password
from app.workers.queue import MAX_ATTEMPTS, claim_next_scan, schedule_retry


def queued_scan(db: Session) -> Scan:
    user = User(email="queue@example.test", password_hash=hash_password("unused-password"))
    db.add(user)
    db.flush()
    profile = IdentityProfile(owner_id=user.id, first_name="Test", last_name="Queue")
    db.add(profile)
    db.flush()
    scan = Scan(owner_id=user.id, profile_id=profile.id, connector_ids=["mock"])
    db.add(scan)
    db.commit()
    return scan


def test_claim_is_exclusive_and_reclaims_expired_lease(tmp_path: Path) -> None:
    database = tmp_path / "queue.db"
    engine = create_engine(f"sqlite:///{database}")
    Base.metadata.create_all(engine)
    now = datetime.now(UTC).replace(tzinfo=None)
    with Session(engine, expire_on_commit=False) as first:
        scan = queued_scan(first)
        assert claim_next_scan(first, "worker-a", now) == scan.id
    with Session(engine) as second:
        assert claim_next_scan(second, "worker-b", now) is None
        claimed = second.get(Scan, scan.id)
        assert claimed is not None
        claimed.lease_expires_at = now - timedelta(seconds=1)
        second.commit()
        assert claim_next_scan(second, "worker-b", now) == scan.id
        second.refresh(claimed)
        assert claimed.lease_owner == "worker-b"
        assert claimed.attempt_count == 2


def test_retry_backoff_becomes_terminal_after_limit(tmp_path: Path) -> None:
    database = tmp_path / "retry.db"
    engine = create_engine(f"sqlite:///{database}")
    Base.metadata.create_all(engine)
    now = datetime.now(UTC).replace(tzinfo=None)
    with Session(engine, expire_on_commit=False) as db:
        scan = queued_scan(db)
        for attempt in range(1, MAX_ATTEMPTS + 1):
            assert claim_next_scan(db, "worker", now) == scan.id
            schedule_retry(db, scan.id, now, jitter_seconds=0)
            db.refresh(scan)
            assert scan.attempt_count == attempt
            if attempt < MAX_ATTEMPTS:
                assert scan.status == ScanStatus.QUEUED
                assert scan.next_attempt_at == now + timedelta(seconds=2**attempt)
                now = scan.next_attempt_at
        assert scan.status == ScanStatus.FAILED
        assert scan.error_code == "connector_error"


def test_expired_last_attempt_is_marked_failed(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'interrupted.db'}")
    Base.metadata.create_all(engine)
    now = datetime.now(UTC).replace(tzinfo=None)
    with Session(engine, expire_on_commit=False) as db:
        scan = queued_scan(db)
        scan.status = ScanStatus.RUNNING
        scan.attempt_count = MAX_ATTEMPTS
        scan.lease_owner = "dead-worker"
        scan.lease_expires_at = now - timedelta(seconds=1)
        db.commit()
        assert claim_next_scan(db, "new-worker", now) is None
        db.refresh(scan)
        assert scan.status == ScanStatus.FAILED
        assert scan.error_code == "worker_interrupted"
        assert scan.lease_owner is None


def test_retry_default_jitter_stays_bounded(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'jitter.db'}")
    Base.metadata.create_all(engine)
    now = datetime.now(UTC).replace(tzinfo=None)
    with Session(engine, expire_on_commit=False) as db:
        scan = queued_scan(db)
        assert claim_next_scan(db, "worker", now) == scan.id
        schedule_retry(db, scan.id, now)
        db.refresh(scan)
        assert scan.next_attempt_at is not None
        delay = (scan.next_attempt_at - now).total_seconds()
        assert 2 <= delay <= 3
