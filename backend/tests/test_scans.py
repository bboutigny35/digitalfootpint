from fastapi.testclient import TestClient


def _create_profile(client: TestClient, csrf: str, name: str = "Alice") -> str:
    response = client.post(
        "/api/v1/profiles",
        headers={"X-CSRF-Token": csrf},
        json={"first_name": name, "last_name": "Martin"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_scan_lifecycle(authenticated: tuple[TestClient, str]) -> None:
    client, csrf = authenticated
    profile_id = _create_profile(client, csrf)
    created = client.post(
        "/api/v1/scans",
        headers={"X-CSRF-Token": csrf},
        json={"profile_id": profile_id, "connector_ids": ["github", "github"]},
    )
    assert created.status_code == 201
    assert created.json()["connector_ids"] == ["github"]
    scan_id = created.json()["id"]
    assert client.get(f"/api/v1/scans/{scan_id}").status_code == 200
    cancelled = client.post(f"/api/v1/scans/{scan_id}/cancel", headers={"X-CSRF-Token": csrf})
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert (
        client.post(f"/api/v1/scans/{scan_id}/cancel", headers={"X-CSRF-Token": csrf}).status_code
        == 409
    )


def test_resources_are_isolated_between_users(authenticated: tuple[TestClient, str]) -> None:
    client, admin_csrf = authenticated
    profile_id = _create_profile(client, admin_csrf)
    scan = client.post(
        "/api/v1/scans",
        headers={"X-CSRF-Token": admin_csrf},
        json={"profile_id": profile_id, "connector_ids": ["github"]},
    ).json()
    created_user = client.post(
        "/api/v1/auth/users",
        headers={"X-CSRF-Token": admin_csrf},
        json={"email": "member@example.com", "password": "member-password-long"},
    )
    assert created_user.status_code == 201
    member_login = client.post(
        "/api/v1/auth/login",
        json={"email": "member@example.com", "password": "member-password-long"},
    )
    member_csrf = member_login.json()["csrf_token"]
    assert client.get(f"/api/v1/profiles/{profile_id}").status_code == 404
    assert client.get(f"/api/v1/scans/{scan['id']}").status_code == 404
    assert (
        client.get(
            "/api/v1/scans/compare/results",
            params={"baseline_scan_id": scan["id"], "current_scan_id": "another-scan"},
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/scans/{scan['id']}/cancel",
            headers={"X-CSRF-Token": member_csrf},
        ).status_code
        == 404
    )
    assert client.get("/api/v1/results").json() == []
    assert (
        client.patch(
            "/api/v1/results/unknown/verification",
            headers={"X-CSRF-Token": member_csrf},
            json={"verification_status": "confirmed"},
        ).status_code
        == 404
    )


def test_scan_rejects_foreign_or_missing_profile(authenticated: tuple[TestClient, str]) -> None:
    client, csrf = authenticated
    response = client.post(
        "/api/v1/scans",
        headers={"X-CSRF-Token": csrf},
        json={"profile_id": "missing", "connector_ids": ["github"]},
    )
    assert response.status_code == 404


def test_scan_rejects_test_or_unknown_connector(authenticated: tuple[TestClient, str]) -> None:
    client, csrf = authenticated
    profile_id = _create_profile(client, csrf)
    for connector_id in ("mock", "unknown"):
        response = client.post(
            "/api/v1/scans",
            headers={"X-CSRF-Token": csrf},
            json={"profile_id": profile_id, "connector_ids": [connector_id]},
        )
        assert response.status_code == 422
        assert response.json()["detail"] == "Connecteur inconnu ou désactivé"


def test_scan_rejects_brave_when_no_api_key_is_configured(
    authenticated: tuple[TestClient, str],
) -> None:
    client, csrf = authenticated
    profile_id = _create_profile(client, csrf)
    response = client.post(
        "/api/v1/scans",
        headers={"X-CSRF-Token": csrf},
        json={"profile_id": profile_id, "connector_ids": ["brave"]},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Un connecteur sélectionné n’est pas configuré"


def test_scan_rejects_unconfigured_searxng(
    authenticated: tuple[TestClient, str], monkeypatch: object
) -> None:
    client, csrf = authenticated
    profile_id = _create_profile(client, csrf)
    monkeypatch.delenv("DIGITALFOOTPRINT_SEARXNG_URL", raising=False)  # type: ignore[attr-defined]
    response = client.post(
        "/api/v1/scans",
        headers={"X-CSRF-Token": csrf},
        json={"profile_id": profile_id, "connector_ids": ["searxng"]},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Un connecteur sélectionné n’est pas configuré"


def test_scan_requires_explicit_consent_for_external_search(
    authenticated: tuple[TestClient, str], monkeypatch: object
) -> None:
    from app.api import scans as scans_api

    client, csrf = authenticated
    profile_id = _create_profile(client, csrf)
    monkeypatch.setattr(scans_api, "connector_is_ready", lambda *_args: True)  # type: ignore[attr-defined]
    response = client.post(
        "/api/v1/scans",
        headers={"X-CSRF-Token": csrf},
        json={"profile_id": profile_id, "connector_ids": ["searxng"]},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Confirmation requise pour la transmission à un moteur de recherche externe"
    )


def test_connector_catalog_lists_only_production_connectors(
    authenticated: tuple[TestClient, str],
) -> None:
    client, _csrf = authenticated
    response = client.get("/api/v1/connectors")
    assert response.status_code == 200
    assert response.json() == [
        {
            "identifier": "brave",
            "version": "1.0",
            "capabilities": ["web_search"],
            "accepted_identifiers": ["name", "pseudonym"],
            "requires_api_key": True,
            "enabled": True,
            "ready": False,
            "health": "not_checked",
            "rate_limit_per_minute": 5,
            "quota_status": "provider_managed",
            "last_scan_at": None,
            "result_count": 0,
            "error_count": 0,
        },
        {
            "identifier": "github",
            "version": "1.0",
            "capabilities": ["public_profiles"],
            "accepted_identifiers": ["pseudonym"],
            "requires_api_key": False,
            "enabled": True,
            "ready": True,
            "health": "not_checked",
            "rate_limit_per_minute": 10,
            "quota_status": "provider_managed",
            "last_scan_at": None,
            "result_count": 0,
            "error_count": 0,
        },
        {
            "identifier": "gitlab",
            "version": "1.0",
            "capabilities": ["public_profiles"],
            "accepted_identifiers": ["pseudonym"],
            "requires_api_key": False,
            "enabled": True,
            "ready": True,
            "health": "not_checked",
            "rate_limit_per_minute": 10,
            "quota_status": "provider_managed",
            "last_scan_at": None,
            "result_count": 0,
            "error_count": 0,
        },
        {
            "identifier": "searxng",
            "version": "1.0",
            "capabilities": ["web_search"],
            "accepted_identifiers": ["name", "pseudonym"],
            "requires_api_key": False,
            "enabled": True,
            "ready": False,
            "health": "not_checked",
            "rate_limit_per_minute": 5,
            "quota_status": "provider_managed",
            "last_scan_at": None,
            "result_count": 0,
            "error_count": 0,
        },
        {
            "identifier": "wayback",
            "version": "1.0",
            "capabilities": ["domain_archives"],
            "accepted_identifiers": ["domain"],
            "requires_api_key": False,
            "enabled": True,
            "ready": True,
            "health": "not_checked",
            "rate_limit_per_minute": 5,
            "quota_status": "provider_managed",
            "last_scan_at": None,
            "result_count": 0,
            "error_count": 0,
        },
    ]


def test_connector_catalog_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/connectors").status_code == 401
