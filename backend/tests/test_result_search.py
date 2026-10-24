from fastapi.testclient import TestClient

from app.core.database import get_db
from app.models.entities import IdentityProfile, Result, Scan, User, VerificationStatus


def test_results_are_filtered_sorted_and_paginated(
    authenticated: tuple[TestClient, str],
) -> None:
    client, _csrf = authenticated
    override = client.app.dependency_overrides[get_db]
    with next(override()) as db:
        user = db.query(User).filter_by(email="owner@example.com").one()
        profile = IdentityProfile(owner_id=user.id, first_name="Alice", last_name="Martin")
        db.add(profile)
        db.flush()
        scan = Scan(owner_id=user.id, profile_id=profile.id, connector_ids=["github"])
        db.add(scan)
        db.flush()
        db.add_all(
            [
                Result(
                    owner_id=user.id,
                    profile_id=profile.id,
                    scan_id=scan.id,
                    connector_id="github",
                    canonical_url="https://github.com/alice",
                    domain="github.com",
                    title="Alice développeuse",
                    snippet="Profil public synthétique",
                    match_type="pseudonym_exact",
                    verification_status=VerificationStatus.CONFIRMED,
                    relevance_score=0.9,
                    score_explanation={"test": True},
                ),
                Result(
                    owner_id=user.id,
                    profile_id=profile.id,
                    scan_id=scan.id,
                    connector_id="github",
                    canonical_url="https://example.test/alice",
                    domain="example.test",
                    title="Autre mention Alice",
                    snippet="Résultat synthétique",
                    match_type="keyword",
                    verification_status=VerificationStatus.UNCERTAIN,
                    relevance_score=0.2,
                    score_explanation={"test": True},
                ),
            ]
        )
        db.commit()

    response = client.get(
        "/api/v1/results/search",
        params={
            "query": "Alice",
            "connector_id": "github",
            "sort_by": "score",
            "sort_order": "desc",
            "page_size": 1,
        },
    )
    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert response.json()["pages"] == 2
    assert response.json()["items"][0]["domain"] == "github.com"

    filtered = client.get(
        "/api/v1/results/search",
        params={"domain": "example.test", "verification_status": "uncertain"},
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["canonical_url"] == "https://example.test/alice"


def test_result_search_rejects_invalid_sort(authenticated: tuple[TestClient, str]) -> None:
    client, _csrf = authenticated
    response = client.get("/api/v1/results/search", params={"sort_by": "unsafe-column"})
    assert response.status_code == 422
