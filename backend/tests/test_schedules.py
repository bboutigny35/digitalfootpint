from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.entities import IdentityProfile, Scan, ScanSchedule, User
from app.security.passwords import hash_password
from app.workers.scheduler import enqueue_due_schedules, next_occurrence


def test_calendar_cadences_handle_month_end() -> None:
    january_end = datetime(2027, 1, 31, 8, 0, tzinfo=UTC)
    assert next_occurrence(january_end, "daily") == january_end + timedelta(days=1)
    assert next_occurrence(january_end, "weekly") == january_end + timedelta(days=7)
    assert next_occurrence(january_end, "monthly") == datetime(2027, 2, 28, 8, 0, tzinfo=UTC)


def test_due_schedule_creates_only_one_scan_and_advances_into_future(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'scheduler.db'}")
    Base.metadata.create_all(engine)
    due_at = datetime(2026, 10, 15, 8, 0, tzinfo=UTC)
    with Session(engine, expire_on_commit=False) as db:
        user = User(email="schedule@example.test", password_hash=hash_password("unused-password"))
        db.add(user)
        db.flush()
        profile = IdentityProfile(owner_id=user.id, first_name="Test", last_name="Schedule")
        db.add(profile)
        db.flush()
        schedule = ScanSchedule(
            owner_id=user.id,
            profile_id=profile.id,
            connector_ids=["github"],
            cadence="daily",
            next_run_at=due_at - timedelta(days=3),
        )
        db.add(schedule)
        db.commit()

        assert enqueue_due_schedules(db, due_at) == 1
        assert enqueue_due_schedules(db, due_at) == 0
        db.refresh(schedule)
        assert schedule.last_run_at is not None
        assert schedule.last_run_at.replace(tzinfo=UTC) == due_at
        assert schedule.next_run_at.replace(tzinfo=UTC) > due_at
        assert db.scalar(select(func.count(Scan.id))) == 1


def test_schedule_api_validates_connector_and_supports_lifecycle(
    authenticated: tuple[TestClient, str],
) -> None:
    client, csrf = authenticated
    profile = client.post(
        "/api/v1/profiles",
        headers={"X-CSRF-Token": csrf},
        json={"first_name": "Test", "last_name": "Surveillance"},
    ).json()
    rejected = client.post(
        "/api/v1/schedules",
        headers={"X-CSRF-Token": csrf},
        json={"profile_id": profile["id"], "connector_ids": ["mock"], "cadence": "daily"},
    )
    assert rejected.status_code == 422
    created = client.post(
        "/api/v1/schedules",
        headers={"X-CSRF-Token": csrf},
        json={
            "profile_id": profile["id"],
            "connector_ids": ["github"],
            "cadence": "weekly",
        },
    )
    assert created.status_code == 201
    schedule_id = created.json()["id"]
    assert client.get("/api/v1/schedules").json()[0]["id"] == schedule_id
    paused = client.patch(
        f"/api/v1/schedules/{schedule_id}",
        headers={"X-CSRF-Token": csrf},
        json={"enabled": False},
    )
    assert paused.status_code == 200
    assert paused.json()["enabled"] is False
    deleted = client.delete(f"/api/v1/schedules/{schedule_id}", headers={"X-CSRF-Token": csrf})
    assert deleted.status_code == 204


def test_external_search_schedule_requires_explicit_consent(
    authenticated: tuple[TestClient, str], monkeypatch: object
) -> None:
    from app.api import schedules as schedules_api

    client, csrf = authenticated
    profile = client.post(
        "/api/v1/profiles",
        headers={"X-CSRF-Token": csrf},
        json={"first_name": "Test", "last_name": "Schedule"},
    ).json()
    monkeypatch.setattr(
        schedules_api, "connector_is_ready", lambda *_args: True
    )  # type: ignore[attr-defined]
    response = client.post(
        "/api/v1/schedules",
        headers={"X-CSRF-Token": csrf},
        json={
            "profile_id": profile["id"],
            "connector_ids": ["searxng"],
            "cadence": "daily",
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"].startswith("Confirmation requise")
