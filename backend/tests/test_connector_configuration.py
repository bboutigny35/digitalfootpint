from typing import Any, cast
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.connectors import configuration as connector_configuration
from app.connectors.configuration import connector_is_ready
from app.connectors.production import build_production_registry
from app.core.config import Settings


def test_admin_disables_connector_and_pending_work(
    authenticated: tuple[TestClient, str],
) -> None:
    client, csrf = authenticated
    profile = client.post(
        "/api/v1/profiles",
        headers={"X-CSRF-Token": csrf},
        json={"first_name": "Alice", "last_name": "Activation"},
    ).json()
    scan = client.post(
        "/api/v1/scans",
        headers={"X-CSRF-Token": csrf},
        json={"profile_id": profile["id"], "connector_ids": ["github"]},
    ).json()
    schedule = client.post(
        "/api/v1/schedules",
        headers={"X-CSRF-Token": csrf},
        json={
            "profile_id": profile["id"],
            "connector_ids": ["github"],
            "cadence": "daily",
        },
    ).json()

    disabled = client.patch(
        "/api/v1/admin/connectors/github",
        headers={"X-CSRF-Token": csrf},
        json={"enabled": False},
    )
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False
    connector_status = client.get("/api/v1/connectors").json()
    assert next(
        item for item in connector_status if item["identifier"] == "github"
    )["enabled"] is False
    assert client.get(f"/api/v1/scans/{scan['id']}").json()["status"] == "cancelled"
    stored_schedule = client.get("/api/v1/schedules").json()[0]
    assert stored_schedule["id"] == schedule["id"]
    assert stored_schedule["enabled"] is False
    rejected = client.post(
        "/api/v1/scans",
        headers={"X-CSRF-Token": csrf},
        json={"profile_id": profile["id"], "connector_ids": ["github"]},
    )
    assert rejected.status_code == 422

    enabled = client.patch(
        "/api/v1/admin/connectors/github",
        headers={"X-CSRF-Token": csrf},
        json={"enabled": True},
    )
    assert enabled.status_code == 200
    created = client.post(
        "/api/v1/scans",
        headers={"X-CSRF-Token": csrf},
        json={"profile_id": profile["id"], "connector_ids": ["github"]},
    )
    assert created.status_code == 201


def test_connector_configuration_requires_admin_and_csrf(
    authenticated: tuple[TestClient, str],
) -> None:
    client, csrf = authenticated
    assert (
        client.patch("/api/v1/admin/connectors/github", json={"enabled": False}).status_code
        == 403
    )
    created = client.post(
        "/api/v1/auth/users",
        headers={"X-CSRF-Token": csrf},
        json={"email": "member-connectors@example.com", "password": "member-password-long"},
    )
    assert created.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "member-connectors@example.com", "password": "member-password-long"},
    )
    member_csrf = login.json()["csrf_token"]
    assert (
        client.patch(
            "/api/v1/admin/connectors/github",
            headers={"X-CSRF-Token": member_csrf},
            json={"enabled": False},
        ).status_code
        == 403
    )


def test_brave_is_not_ready_without_contract_approval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = MagicMock(spec=Session)
    settings = Settings(
        _env_file=None,
        brave_api_token="configured-but-contract-not-approved",  # noqa: S106
        brave_contract_approved=False,
    )
    monkeypatch.setattr(connector_configuration, "get_settings", lambda: settings)

    assert connector_is_ready(database, "brave", requires_api_key=True) is False
    database.get.assert_not_called()


def test_brave_contract_gate_removes_token_from_runtime_connector() -> None:
    blocked = build_production_registry(
        Settings(
            _env_file=None,
            brave_api_token="configured-token",  # noqa: S106
            brave_contract_approved=False,
        )
    ).get("brave")
    approved = build_production_registry(
        Settings(
            _env_file=None,
            brave_api_token="configured-token",  # noqa: S106
            brave_contract_approved=True,
        )
    ).get("brave")

    assert cast(Any, blocked)._token is None
    assert cast(Any, approved)._token == "configured-token"
