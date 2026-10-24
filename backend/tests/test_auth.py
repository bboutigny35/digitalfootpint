from fastapi.testclient import TestClient


def test_bootstrap_login_and_logout(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/bootstrap",
        json={"email": "admin@example.com", "password": "long-enough-password"},
    )
    assert response.status_code == 201
    csrf = response.json()["csrf_token"]
    assert client.get("/api/v1/auth/me").status_code == 200
    assert client.post("/api/v1/auth/logout").status_code == 403
    assert client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "long-enough-password"},
    )
    assert login.status_code == 200


def test_bootstrap_is_single_use(client: TestClient) -> None:
    body = {"email": "admin@example.com", "password": "long-enough-password"}
    assert client.post("/api/v1/auth/bootstrap", json=body).status_code == 201
    assert client.post("/api/v1/auth/bootstrap", json=body).status_code == 409


def test_password_is_not_returned(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/bootstrap",
        json={"email": "admin@example.com", "password": "long-enough-password"},
    )
    assert "password" not in response.text


def test_session_rotation_invalidates_old_csrf(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/bootstrap",
        json={"email": "admin@example.com", "password": "long-enough-password"},
    )
    old_csrf = response.json()["csrf_token"]
    rotated = client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": old_csrf})
    assert rotated.status_code == 200
    new_csrf = rotated.json()["csrf_token"]
    assert new_csrf != old_csrf
    assert client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": old_csrf}).status_code == 403
    assert client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": new_csrf}).status_code == 204


def test_csrf_can_be_restored_for_cookie_session(client: TestClient) -> None:
    bootstrap = client.post(
        "/api/v1/auth/bootstrap",
        json={"email": "admin@example.com", "password": "long-enough-password"},
    )
    old_csrf = bootstrap.json()["csrf_token"]
    restored = client.get("/api/v1/auth/csrf")
    assert restored.status_code == 200
    assert restored.headers["cache-control"] == "no-store"
    new_csrf = restored.json()["csrf_token"]
    assert new_csrf != old_csrf
    assert client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": old_csrf}).status_code == 403
    assert client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": new_csrf}).status_code == 204


def test_csrf_requires_authenticated_session(client: TestClient) -> None:
    assert client.get("/api/v1/auth/csrf").status_code == 401


def test_only_admin_can_create_users(client: TestClient) -> None:
    bootstrap = client.post(
        "/api/v1/auth/bootstrap",
        json={"email": "admin@example.com", "password": "long-enough-password"},
    )
    admin_csrf = bootstrap.json()["csrf_token"]
    created = client.post(
        "/api/v1/auth/users",
        headers={"X-CSRF-Token": admin_csrf},
        json={"email": "member@example.com", "password": "member-password-long"},
    )
    assert created.status_code == 201
    assert created.json()["is_admin"] is False
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "member@example.com", "password": "member-password-long"},
    )
    member_csrf = login.json()["csrf_token"]
    denied = client.post(
        "/api/v1/auth/users",
        headers={"X-CSRF-Token": member_csrf},
        json={"email": "other@example.com", "password": "other-password-long"},
    )
    assert denied.status_code == 403
