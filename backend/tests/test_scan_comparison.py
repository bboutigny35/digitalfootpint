from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.core.database import get_db
from app.models.entities import IdentityProfile, Result, Scan, ScanStatus, User, VerificationStatus
from app.services.scan_comparison import ComparisonCategory, compare_results


def _result(
    scan: Scan,
    url: str,
    title: str,
    status: VerificationStatus = VerificationStatus.UNCERTAIN,
) -> Result:
    return Result(
        owner_id=scan.owner_id,
        profile_id=scan.profile_id,
        scan_id=scan.id,
        connector_id="github",
        canonical_url=url,
        domain="github.com",
        title=title,
        snippet="Profil public",
        match_type="pseudonym_exact",
        verification_status=status,
        relevance_score=0.5,
        score_explanation={"pseudonym": 0.5},
    )


def test_comparison_categories_are_deterministic() -> None:
    baseline_scan = Scan(id="baseline", owner_id="owner", profile_id="profile")
    current_scan = Scan(id="current", owner_id="owner", profile_id="profile")
    baseline = [
        _result(baseline_scan, "https://github.com/known", "Connu"),
        _result(baseline_scan, "https://github.com/changed", "Ancien titre"),
        _result(baseline_scan, "https://github.com/missing", "Non revérifié"),
        _result(
            baseline_scan,
            "https://github.com/excluded",
            "Exclu",
            VerificationStatus.FALSE_POSITIVE,
        ),
    ]
    current = [
        _result(current_scan, "https://github.com/known", "Connu"),
        _result(current_scan, "https://github.com/changed", "Nouveau titre"),
        _result(current_scan, "https://github.com/new", "Nouveau"),
        _result(current_scan, "https://github.com/excluded", "Exclu"),
    ]

    by_url = {item.canonical_url: item for item in compare_results(baseline, current)}

    assert by_url["https://github.com/known"].category == ComparisonCategory.KNOWN
    assert by_url["https://github.com/changed"].category == ComparisonCategory.MODIFIED
    assert by_url["https://github.com/changed"].changed_fields == ("title",)
    assert by_url["https://github.com/new"].category == ComparisonCategory.NEW
    assert by_url["https://github.com/missing"].category == ComparisonCategory.NOT_REVERIFIED
    assert (
        by_url["https://github.com/excluded"].category
        == ComparisonCategory.EXCLUDED_FALSE_POSITIVE
    )


def test_compare_scans_api_is_owned_and_does_not_infer_deletion(
    authenticated: tuple[TestClient, str],
) -> None:
    client, _csrf = authenticated
    override = client.app.dependency_overrides[get_db]
    with next(override()) as db:
        user = db.query(User).filter_by(email="owner@example.com").one()
        profile = IdentityProfile(owner_id=user.id, first_name="Alice", last_name="Martin")
        db.add(profile)
        db.flush()
        baseline = Scan(
            owner_id=user.id,
            profile_id=profile.id,
            status=ScanStatus.COMPLETED,
            connector_ids=["github"],
            created_at=datetime.now(UTC) - timedelta(days=1),
        )
        current = Scan(
            owner_id=user.id,
            profile_id=profile.id,
            status=ScanStatus.COMPLETED,
            connector_ids=["github"],
        )
        db.add_all([baseline, current])
        db.flush()
        db.add(_result(baseline, "https://github.com/absent", "Absent du nouveau scan"))
        db.commit()
        baseline_id, current_id = baseline.id, current.id

    response = client.get(
        "/api/v1/scans/compare/results",
        params={"baseline_scan_id": baseline_id, "current_scan_id": current_id},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["counts"]["not_reverified"] == 1
    assert body["counts"]["inaccessible"] == 0
    assert "jamais considérée comme supprimée" in body["methodology_note"]


def test_compare_scans_rejects_same_or_unfinished_scan(
    authenticated: tuple[TestClient, str],
) -> None:
    client, csrf = authenticated
    profile = client.post(
        "/api/v1/profiles",
        headers={"X-CSRF-Token": csrf},
        json={"first_name": "Alice", "last_name": "Martin"},
    ).json()
    scan = client.post(
        "/api/v1/scans",
        headers={"X-CSRF-Token": csrf},
        json={"profile_id": profile["id"], "connector_ids": ["github"]},
    ).json()
    same = client.get(
        "/api/v1/scans/compare/results",
        params={"baseline_scan_id": scan["id"], "current_scan_id": scan["id"]},
    )
    assert same.status_code == 422
