import asyncio
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.connectors.base import (
    CandidateResult,
    Connector,
    ConnectorMetadata,
    IdentifierType,
    IdentitySnapshot,
)
from app.connectors.mock import MockConnector
from app.connectors.registry import ConnectorRegistry
from app.core.database import Base
from app.models.entities import IdentityProfile, Result, Scan, ScanStatus, User
from app.security.passwords import hash_password
from app.workers import scan_daemon


def _queued_scan(db: Session) -> Scan:
    user = User(email="daemon@example.test", password_hash=hash_password("synthetic-password"))
    db.add(user)
    db.flush()
    profile = IdentityProfile(
        owner_id=user.id,
        first_name="Test",
        last_name="Worker",
        pseudonyms=["test-worker"],
    )
    db.add(profile)
    db.flush()
    scan = Scan(owner_id=user.id, profile_id=profile.id, connector_ids=["mock"])
    db.add(scan)
    db.commit()
    return scan


def test_process_once_persists_results_and_completes_scan(tmp_path: Path, monkeypatch) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'worker.db'}")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        scan = _queued_scan(db)
    monkeypatch.setattr(scan_daemon, "SessionLocal", lambda: Session(engine))
    monkeypatch.setattr(
        scan_daemon,
        "build_registry",
        lambda: ConnectorRegistry([MockConnector()]),
    )

    assert scan_daemon.process_once("test-worker")

    with Session(engine) as db:
        completed = db.get(Scan, scan.id)
        result = db.scalar(select(Result).where(Result.scan_id == scan.id))
        assert completed is not None
        assert completed.status == ScanStatus.COMPLETED
        assert result is not None
        assert result.connector_id == "mock"
    engine.dispose()


class _FailingConnector(Connector):
    metadata = ConnectorMetadata(
        identifier="mock",
        version="test",
        capabilities=("test",),
        accepted_identifiers=(IdentifierType.PSEUDONYM,),
    )

    async def search(self, identity: IdentitySnapshot) -> list[CandidateResult]:
        del identity
        raise RuntimeError("synthetic provider failure")


def test_process_once_requeues_failure_with_generic_error(tmp_path: Path, monkeypatch) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'worker-failure.db'}")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        scan = _queued_scan(db)
    monkeypatch.setattr(scan_daemon, "SessionLocal", lambda: Session(engine))

    assert scan_daemon.process_once("test-worker", ConnectorRegistry([_FailingConnector()]))

    with Session(engine) as db:
        retried = db.get(Scan, scan.id)
        assert retried is not None
        assert retried.status == ScanStatus.QUEUED
        assert retried.error_code == "retry_scheduled"
    engine.dispose()


def test_process_once_requeues_scan_on_graceful_shutdown(tmp_path: Path, monkeypatch) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'worker-shutdown.db'}")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        scan = _queued_scan(db)
    monkeypatch.setattr(scan_daemon, "SessionLocal", lambda: Session(engine))

    async def cancel_run(self: object, scan_id: str, db: Session) -> None:
        del self, scan_id, db
        raise asyncio.CancelledError("worker shutdown")

    monkeypatch.setattr(scan_daemon.ScanRunner, "run", cancel_run)
    assert scan_daemon.process_once("test-worker", ConnectorRegistry([MockConnector()]))

    with Session(engine) as db:
        retried = db.get(Scan, scan.id)
        assert retried is not None
        assert retried.status == ScanStatus.QUEUED
        assert retried.error_code == "retry_scheduled"
    engine.dispose()
