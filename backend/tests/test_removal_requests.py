from fastapi.testclient import TestClient


def test_removal_request_lifecycle_and_manual_letter(
    authenticated: tuple[TestClient, str],
) -> None:
    client, csrf = authenticated
    created = client.post(
        "/api/v1/removal-requests",
        headers={"X-CSRF-Token": csrf},
        json={"organization": "  Exemple SARL  ", "notes": "Demande à préparer"},
    )
    assert created.status_code == 201
    assert created.json()["organization"] == "Exemple SARL"
    assert created.json()["status"] == "draft"
    request_id = created.json()["id"]

    letter = client.get(f"/api/v1/removal-requests/{request_id}/letter")
    assert letter.status_code == 200
    assert "Exemple SARL" in letter.json()["body"]
    assert "envoyer manuellement" in letter.json()["warning"]

    updated = client.patch(
        f"/api/v1/removal-requests/{request_id}",
        headers={"X-CSRF-Token": csrf},
        json={"status": "sent", "requested_at": "2026-10-15T10:00:00Z"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "sent"
    assert len(client.get("/api/v1/removal-requests").json()) == 1

    deleted = client.delete(
        f"/api/v1/removal-requests/{request_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert deleted.status_code == 204
    assert client.get("/api/v1/removal-requests").json() == []


def test_removal_request_rejects_foreign_result_and_requires_csrf(
    authenticated: tuple[TestClient, str],
) -> None:
    client, csrf = authenticated
    missing = client.post(
        "/api/v1/removal-requests",
        headers={"X-CSRF-Token": csrf},
        json={"organization": "Organisme", "result_id": "unknown"},
    )
    assert missing.status_code == 404
    assert (
        client.post(
            "/api/v1/removal-requests",
            json={"organization": "Organisme"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/removal-requests",
            headers={"X-CSRF-Token": csrf},
            json={"organization": "   "},
        ).status_code
        == 422
    )


def test_removal_requests_are_private_between_users(
    authenticated: tuple[TestClient, str],
) -> None:
    client, admin_csrf = authenticated
    request_id = client.post(
        "/api/v1/removal-requests",
        headers={"X-CSRF-Token": admin_csrf},
        json={"organization": "Organisme privé"},
    ).json()["id"]
    assert (
        client.post(
            "/api/v1/auth/users",
            headers={"X-CSRF-Token": admin_csrf},
            json={"email": "removal-member@example.com", "password": "member-password-long"},
        ).status_code
        == 201
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "removal-member@example.com", "password": "member-password-long"},
    )
    member_csrf = login.json()["csrf_token"]
    assert client.get("/api/v1/removal-requests").json() == []
    assert client.get(f"/api/v1/removal-requests/{request_id}/letter").status_code == 404
    assert (
        client.patch(
            f"/api/v1/removal-requests/{request_id}",
            headers={"X-CSRF-Token": member_csrf},
            json={"status": "completed"},
        ).status_code
        == 404
    )
