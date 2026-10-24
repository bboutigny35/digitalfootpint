from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.entities import (
    DiscoveredURL,
    DiscoveryJob,
    IdentityProfile,
    Scan,
    User,
    WebSource,
)
from app.services.discovery_documents import DiscoveryBatch, DiscoveryCandidate
from app.services.discovery_queue import (
    claim_next_discovery_job,
    complete_discovery_job,
    complete_discovery_with_batch,
    enqueue_source_discovery,
    fail_discovery_job,
    schedule_discovery_retry,
)


def make_scan(db: Session) -> Scan:
    user = User(email="discovery-queue@example.test", password_hash="synthetic-hash")  # noqa: S106
    db.add(user)
    db.flush()
    profile = IdentityProfile(owner_id=user.id, first_name="Test", last_name="Discovery Queue")
    db.add(profile)
    db.flush()
    scan = Scan(owner_id=user.id, profile_id=profile.id, connector_ids=[])
    db.add(scan)
    db.commit()
    return scan


def make_source(db: Session, domain: str, priority: int) -> WebSource:
    source = WebSource(
        domain=domain,
        base_url=f"https://{domain}/sitemap.xml",
        category="public",
        access_method="sitemap",
        state="active",
        priority=priority,
    )
    db.add(source)
    db.commit()
    return source


def test_discovery_jobs_are_deduplicated_and_claimed_by_priority(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path}/discovery-queue.db")
    Base.metadata.create_all(engine)
    now = datetime(2026, 1, 1, tzinfo=UTC)
    with Session(engine) as db:
        scan = make_scan(db)
        later = make_source(db, "later.example", 200)
        first = make_source(db, "first.example", 10)
        later_job = enqueue_source_discovery(db, scan, later)
        first_job = enqueue_source_discovery(db, scan, first)
        duplicate = enqueue_source_discovery(db, scan, first)
        assert later_job.created is True
        assert first_job.created is True
        assert duplicate.created is False
        assert duplicate.job.id == first_job.job.id
        assert claim_next_discovery_job(db, "worker", now) == first_job.job.id
    engine.dispose()


def test_discovery_retry_is_bounded_and_checks_lease_owner(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path}/discovery-retry.db")
    Base.metadata.create_all(engine)
    now = datetime(2026, 1, 1, tzinfo=UTC)
    with Session(engine) as db:
        scan = make_scan(db)
        source = make_source(db, "retry.example", 10)
        queued = enqueue_source_discovery(db, scan, source)
        for attempt in range(3):
            assert claim_next_discovery_job(db, "worker", now) == queued.job.id
            schedule_discovery_retry(
                db,
                queued.job.id,
                worker_id="stale-worker",
                error_code="network_error",
                now=now,
            )
            db.refresh(queued.job)
            assert queued.job.status == "running"
            schedule_discovery_retry(
                db,
                queued.job.id,
                worker_id="worker",
                error_code="network_error",
                retry_after_seconds=999999,
                jitter_seconds=0,
                now=now,
            )
            db.refresh(queued.job)
            if attempt < 2:
                assert queued.job.next_attempt_at is not None
                now = queued.job.next_attempt_at.replace(tzinfo=UTC)
        assert queued.job.status == "failed"
        assert queued.job.error_code == "network_error"
    engine.dispose()


def test_discovery_completion_and_terminal_failure_are_lease_safe(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path}/discovery-terminal.db")
    Base.metadata.create_all(engine)
    now = datetime(2026, 1, 1, tzinfo=UTC)
    with Session(engine) as db:
        scan = make_scan(db)
        source = make_source(db, "complete.example", 10)
        queued = enqueue_source_discovery(db, scan, source)
        assert claim_next_discovery_job(db, "worker", now) == queued.job.id
        complete_discovery_job(db, queued.job.id, worker_id="stale-worker", now=now)
        db.refresh(queued.job)
        assert queued.job.status == "running"
        complete_discovery_job(db, queued.job.id, worker_id="worker", now=now)
        db.refresh(queued.job)
        assert queued.job.status == "completed"

        other_source = make_source(db, "failed.example", 20)
        failed = enqueue_source_discovery(db, scan, other_source)
        assert claim_next_discovery_job(db, "worker", now) == failed.job.id
        fail_discovery_job(
            db, failed.job.id, worker_id="worker", error_code="invalid_document", now=now
        )
        stored = db.get(DiscoveryJob, failed.job.id)
        assert stored is not None
        assert stored.status == "failed"
        assert stored.error_code == "invalid_document"
    engine.dispose()


def test_discovery_batch_is_not_persisted_after_lease_expiry(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path}/discovery-expired.db")
    Base.metadata.create_all(engine)
    now = datetime(2026, 1, 1, tzinfo=UTC)
    with Session(engine) as db:
        scan = make_scan(db)
        source = make_source(db, "expired.example", 10)
        queued = enqueue_source_discovery(db, scan, source)
        assert claim_next_discovery_job(db, "worker", now) == queued.job.id

        result = complete_discovery_with_batch(
            db,
            queued.job.id,
            DiscoveryBatch(
                items=(
                    DiscoveryCandidate(
                        url="https://expired.example/profile",
                        kind="page",
                    ),
                )
            ),
            worker_id="worker",
            now=now + timedelta(minutes=6),
        )

        assert result is None
        assert db.query(DiscoveredURL).count() == 0
        db.refresh(queued.job)
        assert queued.job.status == "running"
    engine.dispose()
