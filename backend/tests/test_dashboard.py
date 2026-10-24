from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.core.database import get_db
from app.models.entities import IdentityProfile, Result, Scan, User, VerificationStatus


def test_dashboard_aggregates_only_owned_data(authenticated: tuple[TestClient, str]) -> None:
    client, _csrf = authenticated
    override = client.app.dependency_overrides[get_db]
    with next(override()) as db:
        owner = db.query(User).filter_by(email="owner@example.com").one()
        profile = IdentityProfile(owner_id=owner.id, first_name="Alice", last_name="Martin")
        db.add(profile)
        db.flush()
        scan = Scan(owner_id=owner.id, profile_id=profile.id, connector_ids=["github"])
        db.add(scan)
        db.flush()
        db.add_all(
            [
                Result(
                    owner_id=owner.id,
                    profile_id=profile.id,
                    scan_id=scan.id,
                    connector_id="github",
                    canonical_url="https://github.com/alice",
                    domain="github.com",
                    title="Alice",
                    snippet="Synthétique",
                    match_type="pseudonym_exact",
                    relevance_score=0.8,
                    score_explanation={"test": True},
                    discovered_at=datetime.now(UTC),
                ),
                Result(
                    owner_id=owner.id,
                    profile_id=profile.id,
                    scan_id=scan.id,
                    connector_id="github",
                    canonical_url="https://github.com/alice-old",
                    domain="github.com",
                    title="Alice historique",
                    snippet="Synthétique",
                    match_type="pseudonym_exact",
                    verification_status=VerificationStatus.CONFIRMED,
                    relevance_score=0.8,
                    score_explanation={"test": True},
                    discovered_at=datetime.now(UTC) - timedelta(days=10),
                ),
            ]
        )
        db.commit()

    response = client.get("/api/v1/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert body["total_mentions"] == 2
    assert body["total_domains"] == 1
    assert body["total_profiles"] == 1
    assert body["new_mentions_7d"] == 1
    assert body["needs_verification"] == 1
    assert len(body["evolution"]) == 30
    assert sum(point["mentions"] for point in body["evolution"]) == 2


def test_dashboard_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/dashboard").status_code == 401
