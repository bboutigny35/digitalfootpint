from fastapi.testclient import TestClient

PROFILE = {
    "first_name": "Alice",
    "last_name": "Martin",
    "pseudonyms": ["alice_m"],
    "emails": ["alice@example.com"],
    "websites": ["https://example.com/me"],
}


def test_profile_crud_requires_csrf(authenticated: tuple[TestClient, str]) -> None:
    client, csrf = authenticated
    assert client.post("/api/v1/profiles", json=PROFILE).status_code == 403
    created = client.post("/api/v1/profiles", json=PROFILE, headers={"X-CSRF-Token": csrf})
    assert created.status_code == 201
    profile_id = created.json()["id"]
    assert client.get("/api/v1/profiles").json()[0]["pseudonyms"] == ["alice_m"]
    updated = {**PROFILE, "context": "Développeuse à Lyon"}
    response = client.put(
        f"/api/v1/profiles/{profile_id}", json=updated, headers={"X-CSRF-Token": csrf}
    )
    assert response.status_code == 200
    assert response.json()["context"] == "Développeuse à Lyon"
    assert (
        client.delete(f"/api/v1/profiles/{profile_id}", headers={"X-CSRF-Token": csrf}).status_code
        == 204
    )
    assert client.get(f"/api/v1/profiles/{profile_id}").status_code == 404


def test_profiles_require_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/profiles").status_code == 401
