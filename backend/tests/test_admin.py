from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import admin as admin_api
from app.core.database import get_db
from app.models.entities import AuditEvent, PlatformCatalogEntry, User


def test_admin_overview_and_audit_do_not_expose_secrets(
    authenticated: tuple[TestClient, str],
) -> None:
    client, _csrf = authenticated
    overview = client.get("/api/v1/admin/overview")
    assert overview.status_code == 200
    assert overview.json()["application_version"] == "0.1.0-dev"
    assert overview.json()["database_backend"] == "sqlite"
    assert "database_url" not in overview.json()
    assert "github_api_token" not in overview.json()

    override = client.app.dependency_overrides[get_db]
    with next(override()) as db:
        owner = db.query(User).filter_by(email="owner@example.com").one()
        db.add(
            AuditEvent(
                actor_id=owner.id,
                action="test.redaction",
                resource_type="test",
                details={"status": "ok", "api_key": "synthetic-secret-value"},
            )
        )
        db.commit()

    events = client.get(
        "/api/v1/admin/audit-events",
        params={"action": "test.redaction", "page_size": 10},
    )
    assert events.status_code == 200
    assert events.json()["total"] == 1
    assert events.json()["items"][0]["details"] == {"status": "ok"}
    assert "a-strong-test-password" not in events.text
    assert "synthetic-secret-value" not in events.text


def test_non_admin_cannot_access_administration(
    authenticated: tuple[TestClient, str],
) -> None:
    client, csrf = authenticated
    created = client.post(
        "/api/v1/auth/users",
        headers={"X-CSRF-Token": csrf},
        json={"email": "ordinary@example.com", "password": "member-password-long"},
    )
    assert created.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "ordinary@example.com", "password": "member-password-long"},
    )
    assert login.status_code == 200
    assert client.get("/api/v1/admin/overview").status_code == 403
    assert client.get("/api/v1/admin/audit-events").status_code == 403
    assert client.get("/api/v1/admin/connector-secrets").status_code == 403
    assert client.get("/api/v1/admin/platform-catalog").status_code == 403
    assert client.get("/api/v1/admin/web-sources").status_code == 403
    assert client.post("/api/v1/admin/backups/download").status_code == 403


def test_admin_platform_catalog_and_web_sources(
    authenticated: tuple[TestClient, str],
) -> None:
    client, csrf = authenticated
    override = client.app.dependency_overrides[get_db]
    with next(override()) as db:
        db.add(
            PlatformCatalogEntry(
                identifier="netflix",
                display_name="Netflix",
                category="streaming",
                verification_method="none",
                default_status="NOT_VERIFIABLE",
                priority=200,
                limitations="Aucun annuaire public de comptes clients.",
            )
        )
        db.commit()

    catalog = client.get("/api/v1/admin/platform-catalog?category=streaming")
    assert catalog.status_code == 200
    assert catalog.json()[0]["default_status"] == "NOT_VERIFIABLE"
    assert catalog.json()[0]["connector_id"] is None

    payload = {
        "base_url": "https://example.net/public/",
        "category": "Public feeds",
        "access_method": "feed",
        "priority": 40,
        "cache_ttl_seconds": 3600,
        "rate_limit_per_minute": 3,
        "restrictions": [" public only ", "public only"],
    }
    assert client.post("/api/v1/admin/web-sources", json=payload).status_code == 403
    created = client.post(
        "/api/v1/admin/web-sources",
        json=payload,
        headers={"X-CSRF-Token": csrf},
    )
    assert created.status_code == 201
    source = created.json()
    assert source["domain"] == "example.net"
    assert source["state"] == "pending"
    assert source["category"] == "public_feeds"
    assert source["restrictions"] == ["public only"]
    assert (
        client.post(
            "/api/v1/admin/web-sources",
            json=payload,
            headers={"X-CSRF-Token": csrf},
        ).status_code
        == 409
    )
    updated = client.patch(
        f"/api/v1/admin/web-sources/{source['id']}",
        json={"state": "active", "priority": 90},
        headers={"X-CSRF-Token": csrf},
    )
    assert updated.status_code == 200
    assert updated.json()["state"] == "active"
    assert client.get("/api/v1/admin/web-sources").json()[0]["priority"] == 90


def test_admin_downloads_ephemeral_backup_without_choosing_path(
    authenticated: tuple[TestClient, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, csrf = authenticated
    created_paths: list[Path] = []

    def fake_archive(_database_url: str, destination: Path) -> Path:
        created_paths.append(destination)
        destination.write_bytes(b"synthetic-backup-content")
        destination.chmod(0o600)
        return destination

    monkeypatch.setattr(admin_api, "create_archive", fake_archive)
    response = client.post(
        "/api/v1/admin/backups/download",
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 200
    assert response.content == b"synthetic-backup-content"
    assert response.headers["cache-control"] == "no-store"
    assert "digitalfootprint-backup-" in response.headers["content-disposition"]
    assert created_paths and not created_paths[0].parent.exists()
    audit = client.get(
        "/api/v1/admin/audit-events",
        params={"action": "backup.download"},
    )
    assert audit.json()["total"] == 1
    assert "database_url" not in audit.text


def test_backup_download_requires_csrf_and_serializes_execution(
    authenticated: tuple[TestClient, str],
) -> None:
    client, _csrf = authenticated
    assert client.post("/api/v1/admin/backups/download").status_code == 403
    assert admin_api._backup_lock.acquire(blocking=False)
    try:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "owner@example.com", "password": "a-strong-test-password"},
        )
        response = client.post(
            "/api/v1/admin/backups/download",
            headers={"X-CSRF-Token": login.json()["csrf_token"]},
        )
        assert response.status_code == 409
    finally:
        admin_api._backup_lock.release()
