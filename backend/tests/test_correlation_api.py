from datetime import UTC, datetime
from typing import cast

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.main import app
from app.models.entities import (
    Evidence,
    EvidenceMatch,
    IdentityCorrelation,
    Result,
    Scan,
    User,
    UserValidation,
    VerificationStatus,
)


def _create_profile(client: TestClient, csrf: str, first_name: str) -> str:
    response = client.post(
        "/api/v1/profiles",
        headers={"X-CSRF-Token": csrf},
        json={"first_name": first_name, "last_name": "Martin"},
    )
    assert response.status_code == 201
    return cast(str, response.json()["id"])


def _seed_correlation(profile_id: str) -> tuple[str, str]:
    dependency = app.dependency_overrides[get_db]
    session_generator = dependency()
    db: Session = next(session_generator)
    try:
        owner = db.scalar(select(User).where(User.email == "owner@example.com"))
        assert owner is not None
        scan = Scan(owner_id=owner.id, profile_id=profile_id, connector_ids=[])
        db.add(scan)
        db.flush()
        result = Result(
            owner_id=owner.id,
            profile_id=profile_id,
            scan_id=scan.id,
            connector_id="synthetic",
            canonical_url="https://profiles.example/alice",
            domain="profiles.example",
            title="Alice profile",
            snippet="Public profile",
            match_type="profile",
            relevance_score=0.6,
            score_explanation={"method": "test"},
        )
        db.add(result)
        db.flush()
        evidence = Evidence(
            owner_id=owner.id,
            scan_id=scan.id,
            result_id=result.id,
            evidence_type="identity_criteria",
            excerpt="Alice Martin",
            source_url=result.canonical_url,
            source_hash="a" * 64,
            provenance={"method": "test"},
            observed_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        db.add(evidence)
        db.flush()
        db.add(
            EvidenceMatch(
                evidence_id=evidence.id,
                criterion_type="name",
                criterion_hash="b" * 64,
                match_kind="exact_text",
                weight=0.15,
                explanation="Nom exact présent dans la page",
            )
        )
        correlation = IdentityCorrelation(
            owner_id=owner.id,
            result_id=result.id,
            relevance_score=0.6,
            attribution_score=0.15,
            explanation={"method": "test"},
            contradictions=[],
            evidence_count=1,
        )
        db.add(correlation)
        db.commit()
        return result.id, correlation.id
    finally:
        session_generator.close()


def test_private_correlation_review_and_attribution_correction(
    authenticated: tuple[TestClient, str],
) -> None:
    client, csrf = authenticated
    original_profile_id = _create_profile(client, csrf, "Alice")
    corrected_profile_id = _create_profile(client, csrf, "Alicia")
    result_id, correlation_id = _seed_correlation(original_profile_id)

    read = client.get(f"/api/v1/results/{result_id}/correlation")
    assert read.status_code == 200
    assert read.json()["attribution_score"] == 0.15
    assert read.json()["validation"] is None
    assert read.json()["evidence"][0]["matches"][0]["criterion_type"] == "name"
    assert "criterion_hash" not in read.json()["evidence"][0]["matches"][0]

    assert (
        client.put(
            f"/api/v1/results/{result_id}/correlation/validation",
            json={"decision": "confirmed"},
        ).status_code
        == 403
    )
    reviewed = client.put(
        f"/api/v1/results/{result_id}/correlation/validation",
        headers={"X-CSRF-Token": csrf},
        json={
            "decision": "confirmed",
            "attributed_profile_id": corrected_profile_id,
            "add_confirmed_profile": True,
        },
    )
    assert reviewed.status_code == 200
    validation = reviewed.json()["validation"]
    assert validation["decision"] == "confirmed"
    assert validation["attributed_profile_id"] == corrected_profile_id
    assert validation["reused_from_validation_id"] is None

    corrected = client.get(f"/api/v1/profiles/{corrected_profile_id}").json()
    assert corrected["confirmed_profiles"] == ["https://profiles.example/alice"]
    dependency = app.dependency_overrides[get_db]
    generator = dependency()
    db: Session = next(generator)
    try:
        result = db.get(Result, result_id)
        assert result is not None
        assert result.verification_status == VerificationStatus.CONFIRMED
        stored = db.scalar(
            select(UserValidation).where(UserValidation.correlation_id == correlation_id)
        )
        assert stored is not None
        assert stored.owner_id == result.owner_id
    finally:
        generator.close()


def test_correlation_review_rejects_incoherent_payload(
    authenticated: tuple[TestClient, str],
) -> None:
    client, csrf = authenticated
    profile_id = _create_profile(client, csrf, "Alice")
    result_id, _correlation_id = _seed_correlation(profile_id)
    response = client.put(
        f"/api/v1/results/{result_id}/correlation/validation",
        headers={"X-CSRF-Token": csrf},
        json={"decision": "uncertain", "exclusion_kind": "homonym"},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Une exclusion exige le rejet de la correspondance"

    created_user = client.post(
        "/api/v1/auth/users",
        headers={"X-CSRF-Token": csrf},
        json={"email": "reviewer@example.com", "password": "reviewer-password-long"},
    )
    assert created_user.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "reviewer@example.com", "password": "reviewer-password-long"},
    )
    assert login.status_code == 200
    assert client.get(f"/api/v1/results/{result_id}/correlation").status_code == 404
