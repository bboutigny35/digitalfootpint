from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.entities import (
    IdentityProfile,
    Notification,
    NotificationPreference,
    Result,
    Scan,
    ScanStatus,
    User,
)
from app.security.passwords import hash_password
from app.services.notifications import create_new_mention_notification


def _result(scan: Scan, url: str) -> Result:
    return Result(
        owner_id=scan.owner_id,
        profile_id=scan.profile_id,
        scan_id=scan.id,
        connector_id="mock",
        canonical_url=url,
        domain="example.test",
        title=url.rsplit("/", 1)[-1],
        snippet="Donnée synthétique",
        match_type="test",
        relevance_score=0.2,
        score_explanation={"method": "test"},
    )


def test_new_mentions_create_one_minimized_notification() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        user = User(email="notify@example.test", password_hash=hash_password("unused-password"))
        db.add(user)
        db.flush()
        profile = IdentityProfile(owner_id=user.id, first_name="Alice", last_name="Martin")
        db.add(profile)
        db.flush()
        baseline = Scan(
            owner_id=user.id,
            profile_id=profile.id,
            status=ScanStatus.COMPLETED,
            connector_ids=["mock"],
        )
        db.add(baseline)
        db.flush()
        current = Scan(
            owner_id=user.id,
            profile_id=profile.id,
            status=ScanStatus.RUNNING,
            connector_ids=["mock"],
        )
        db.add(current)
        db.flush()
        # Force un ordre stable sans attendre l'horloge.
        current.created_at = baseline.created_at + timedelta(microseconds=1)
        db.add_all(
            [
                _result(baseline, "https://example.test/known"),
                _result(current, "https://example.test/known"),
                _result(current, "https://example.test/new"),
            ]
        )
        db.flush()

        notification = create_new_mention_notification(current, db)
        db.flush()

        assert notification is not None
        assert notification.message.startswith("1 nouvelle(s) mention(s)")
        assert "example.test/new" not in notification.message
        assert create_new_mention_notification(current, db) is None


def test_disabled_preference_prevents_notification() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        user = User(email="disabled@example.test", password_hash=hash_password("unused-password"))
        db.add(user)
        db.flush()
        profile = IdentityProfile(owner_id=user.id, first_name="Alice", last_name="Martin")
        db.add(profile)
        db.flush()
        scan = Scan(owner_id=user.id, profile_id=profile.id, connector_ids=["mock"])
        db.add(scan)
        db.add(NotificationPreference(owner_id=user.id, notify_new_mentions=False))
        db.flush()
        assert create_new_mention_notification(scan, db) is None
        assert db.scalar(select(Notification)) is None


def test_notification_preferences_require_csrf(
    authenticated: tuple[TestClient, str],
) -> None:
    client, csrf = authenticated
    assert client.get("/api/v1/notifications/preferences").json() == {
        "notify_new_mentions": True
    }
    assert (
        client.patch(
            "/api/v1/notifications/preferences",
            json={"notify_new_mentions": False},
        ).status_code
        == 403
    )
    changed = client.patch(
        "/api/v1/notifications/preferences",
        headers={"X-CSRF-Token": csrf},
        json={"notify_new_mentions": False},
    )
    assert changed.status_code == 200
    assert changed.json() == {"notify_new_mentions": False}
