import asyncio

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.connectors.mock import MockConnector
from app.connectors.registry import ConnectorRegistry
from app.connectors.wayback import WaybackConnector
from app.core.database import Base
from app.models.entities import IdentityProfile, Result, Scan, ScanStatus, User
from app.security.passwords import hash_password
from app.workers.runner import ScanRunner


def test_worker_persists_mock_result_without_network() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        user = User(
            email="worker@example.com",
            password_hash=hash_password("not-used-by-this-test"),
        )
        db.add(user)
        db.flush()
        profile = IdentityProfile(
            owner_id=user.id,
            first_name="Alice",
            last_name="Martin",
            pseudonyms=["alice_m"],
        )
        db.add(profile)
        db.flush()
        scan = Scan(owner_id=user.id, profile_id=profile.id, connector_ids=["mock"])
        db.add(scan)
        db.commit()
        asyncio.run(ScanRunner(ConnectorRegistry([MockConnector()])).run(scan.id, db))
        db.refresh(scan)
        result = db.scalar(select(Result).where(Result.scan_id == scan.id))
        assert scan.status == ScanStatus.COMPLETED
        assert scan.progress == 1.0
        assert result is not None
        assert result.connector_id == "mock"
        assert result.relevance_score == 0.2
        assert result.score_explanation["method"] == "weighted-signals-v1"


def test_worker_passes_profile_websites_to_wayback_connector() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json=[
                ["timestamp", "original", "statuscode"],
                ["20240102030405", "https://example.test/", "200"],
            ],
        )

    with Session(engine, expire_on_commit=False) as db:
        user = User(
            email="wayback-worker@example.test",
            password_hash=hash_password("not-used-by-this-test"),
        )
        db.add(user)
        db.flush()
        profile = IdentityProfile(
            owner_id=user.id,
            first_name="Alice",
            last_name="Martin",
            websites=["https://example.test/profile"],
        )
        db.add(profile)
        db.flush()
        scan = Scan(owner_id=user.id, profile_id=profile.id, connector_ids=["wayback"])
        db.add(scan)
        db.commit()

        async def run() -> None:
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                registry = ConnectorRegistry([WaybackConnector(client=client)])
                await ScanRunner(registry).run(scan.id, db)

        asyncio.run(run())
        db.refresh(scan)
        result = db.scalar(select(Result).where(Result.scan_id == scan.id))
        assert scan.status == ScanStatus.COMPLETED
        assert result is not None
        assert result.connector_id == "wayback"
        assert result.canonical_url == (
            "https://web.archive.org/web/20240102030405/https://example.test/"
        )
        assert len(requests) == 1
        assert requests[0].url.params["url"] == "example.test"
