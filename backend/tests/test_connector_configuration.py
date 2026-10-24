from fastapi.testclient import TestClient


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
