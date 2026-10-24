import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import Connection, Engine

os.environ["DIGITALFOOTPRINT_DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["DIGITALFOOTPRINT_SECRET_KEY"] = "test-secret-key-with-at-least-32-characters"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, get_db
from app.main import app


@pytest.fixture(autouse=True)
def dispose_test_engines() -> Generator[None, None, None]:
    engines: set[Engine] = set()

    def track_engine(connection: Connection) -> None:
        engines.add(connection.engine)

    event.listen(Engine, "engine_connect", track_engine)
    try:
        yield
    finally:
        event.remove(Engine, "engine_connect", track_engine)
        for engine in engines:
            engine.dispose()


@pytest.fixture
def client(tmp_path: Path) -> Generator[TestClient, None, None]:
    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / 'api-test.db'}",
        connect_args={"check_same_thread": False},
    )
    TestingSession = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        Base.metadata.create_all(engine)

        def override_db() -> Generator[Session, None, None]:
            with TestingSession() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        # uvloop évite un blocage du portail asyncio standard observé sous Python 3.13.
        with TestClient(
            app,
            base_url="http://localhost",
            backend_options={"use_uvloop": True},
        ) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def authenticated(client: TestClient) -> tuple[TestClient, str]:
    response = client.post(
        "/api/v1/auth/bootstrap",
        json={"email": "owner@example.com", "password": "a-strong-test-password"},
    )
    assert response.status_code == 201
    return client, response.json()["csrf_token"]
