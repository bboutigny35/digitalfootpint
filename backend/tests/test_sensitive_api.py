import logging

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import get_db
from app.main import app
from app.models.entities import User
from app.sensitive_monitor.models import SensitiveAlert, SensitiveCheck, SensitiveFinding
from app.sensitive_monitor.types import (
    CheckStatus,
    FindingStatus,
    RiskLevel,
    SensitiveCategory,
)
from tests.test_sensitive_validation import synthetic_nir


def test_ephemeral_nir_is_masked_and_not_logged(
    authenticated: tuple[TestClient, str], caplog: object
) -> None:
    client, csrf = authenticated
    nir = synthetic_nir("1000199999999")
    with caplog.at_level(logging.DEBUG):  # type: ignore[attr-defined]
        response = client.post(
            "/api/v1/sensitive-monitor/validate",
            headers={"X-CSRF-Token": csrf},
            json={"category": "nir", "value": nir},
        )
    assert response.status_code == 200
    assert response.json()["valid"] is True
    assert nir not in response.text
    assert nir not in caplog.text  # type: ignore[attr-defined]


def test_descriptor_never_returns_raw_value(authenticated: tuple[TestClient, str]) -> None:
    client, csrf = authenticated
    phone = "+33612345678"
    response = client.post(
        "/api/v1/sensitive-monitor/descriptors",
        headers={"X-CSRF-Token": csrf},
        json={"category": "phone", "value": phone, "retention_days": 30},
    )
    assert response.status_code == 201
    payload = response.json()
    assert phone not in response.text
    assert "fingerprint" not in payload
    descriptor_id = payload["id"]
    history = client.post(
        "/api/v1/sensitive-monitor/checks/local",
        headers={"X-CSRF-Token": csrf},
        json={"descriptor_id": descriptor_id},
    )
    assert history.status_code == 201
    assert history.json()["external_transmission"] is False
    assert client.get("/api/v1/sensitive-monitor/checks").status_code == 200
    deleted = client.delete(
        f"/api/v1/sensitive-monitor/descriptors/{descriptor_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert deleted.status_code == 204
    assert client.get("/api/v1/sensitive-monitor/descriptors").json() == []


def test_pan_and_cvv_cannot_be_submitted(authenticated: tuple[TestClient, str]) -> None:
    client, csrf = authenticated
    response = client.post(
        "/api/v1/sensitive-monitor/cards",
        headers={"X-CSRF-Token": csrf},
        json={
            "payment_network": "Test Network",
            "last_four": "4242",
            "pan": "4242424242424242",
            "cvv": "123",
        },
    )
    assert response.status_code == 422
    accepted = client.post(
        "/api/v1/sensitive-monitor/cards",
        headers={"X-CSRF-Token": csrf},
        json={"payment_network": "Test Network", "last_four": "4242"},
    )
    assert accepted.status_code == 201
    assert "4242424242424242" not in accepted.text


def test_sensitive_routes_require_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/sensitive-monitor/descriptors").status_code == 401
    assert client.get("/api/v1/sensitive-monitor/checks").status_code == 401
    assert client.get("/api/v1/sensitive-monitor/findings").status_code == 401
    assert client.get("/api/v1/sensitive-monitor/alerts").status_code == 401
    assert (
        client.post(
            "/api/v1/sensitive-monitor/validate",
            json={"category": "id_document", "value": "TEST-DOC-123"},
        ).status_code
        == 401
    )


def test_sensitive_values_are_body_only_in_openapi(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    for path in paths:
        assert "{value}" not in path
        assert "nir" not in path.lower()
        assert "iban" not in path.lower()
        assert "pan" not in path.lower()


def test_alerts_are_private_and_can_be_acknowledged(
    authenticated: tuple[TestClient, str],
) -> None:
    client, admin_csrf = authenticated
    dependency = app.dependency_overrides[get_db]()
    db = next(dependency)
    owner = db.scalar(select(User).where(User.email == "owner@example.com"))
    assert owner is not None
    check = SensitiveCheck(
        owner_id=owner.id,
        category=SensitiveCategory.PHONE,
        provider_id="authorized-test-source",
        status=CheckStatus.COMPLETED,
        external_transmission=False,
    )
    db.add(check)
    db.flush()
    finding = SensitiveFinding(
        owner_id=owner.id,
        check_id=check.id,
        category=SensitiveCategory.PHONE,
        source_label="authorized-test-source",
        risk_level=RiskLevel.HIGH,
        verification_status=FindingStatus.CONFIRMED,
        recommendation="Contacter l’opérateur et renforcer la sécurité du compte.",
    )
    db.add(finding)
    db.flush()
    alert = SensitiveAlert(
        owner_id=owner.id,
        finding_id=finding.id,
        category=SensitiveCategory.PHONE,
        source_label="authorized-test-source",
        risk_level=RiskLevel.HIGH,
        recommendation=finding.recommendation,
    )
    db.add(alert)
    db.commit()
    alert_id = alert.id
    dependency.close()

    created = client.post(
        "/api/v1/auth/users",
        headers={"X-CSRF-Token": admin_csrf},
        json={"email": "other@example.com", "password": "other-password-long"},
    )
    assert created.status_code == 201
    other_login = client.post(
        "/api/v1/auth/login",
        json={"email": "other@example.com", "password": "other-password-long"},
    )
    other_csrf = other_login.json()["csrf_token"]
    assert client.get("/api/v1/sensitive-monitor/alerts").json() == []
    denied = client.post(
        f"/api/v1/sensitive-monitor/alerts/{alert_id}/acknowledge",
        headers={"X-CSRF-Token": other_csrf},
    )
    assert denied.status_code == 404

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "a-strong-test-password"},
    )
    restored_csrf = admin_login.json()["csrf_token"]
    alerts = client.get("/api/v1/sensitive-monitor/alerts")
    assert alerts.status_code == 200
    assert alerts.json()[0]["recommendation"] == finding.recommendation
    assert "masked_label" not in alerts.text
    assert client.get("/api/v1/sensitive-monitor/findings").status_code == 200
    assert (
        client.post(f"/api/v1/sensitive-monitor/alerts/{alert_id}/acknowledge").status_code == 403
    )
    acknowledged = client.post(
        f"/api/v1/sensitive-monitor/alerts/{alert_id}/acknowledge",
        headers={"X-CSRF-Token": restored_csrf},
    )
    assert acknowledged.status_code == 200
    assert acknowledged.json()["acknowledged_at"] is not None
