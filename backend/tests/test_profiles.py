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


def test_profile_normalizes_extended_identity_fields(authenticated: tuple[TestClient, str]) -> None:
    client, csrf = authenticated
    response = client.post(
        "/api/v1/profiles",
        json={
            **PROFILE,
            "first_name": "  Alïce  ",
            "former_pseudonyms": [" old-alice ", "OLD-ALICE"],
            "phone_numbers": ["+33 (0) 6 12 34 56 78", "0033 6 12 34 56 78"],
            "city_region": "  Lyon   Métropole ",
            "profession": " Ingénieure ",
            "employers": [" Example  SA "],
            "confirmed_profiles": ["https://example.com/alice"],
            "exact_phrases": [" conférence   sécurité "],
            "exclusions": [" homonyme ", "HOMONYME"],
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["first_name"] == "Alïce"
    assert body["former_pseudonyms"] == ["old-alice"]
    assert body["phone_numbers"] == ["+330612345678", "+33612345678"]
    assert body["city_region"] == "Lyon Métropole"
    assert body["profession"] == "Ingénieure"
    assert body["employers"] == ["Example SA"]
    assert body["exact_phrases"] == ["conférence sécurité"]
    assert body["exclusions"] == ["homonyme"]


def test_profile_rejects_invalid_phone(authenticated: tuple[TestClient, str]) -> None:
    client, csrf = authenticated
    response = client.post(
        "/api/v1/profiles",
        json={**PROFILE, "phone_numbers": ["not-a-phone"]},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 422
