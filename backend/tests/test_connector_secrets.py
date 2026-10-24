import base64

import pytest
from fastapi.testclient import TestClient

from app.api import admin as admin_api
from app.core.config import Settings
from app.security.connector_secrets import ConnectorSecretVault, SecretVaultError


def _encoded(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode()


def _vault(*, active: str = "v1", include_v2: bool = False) -> ConnectorSecretVault:
    keys = [f"v1:{_encoded(b'a' * 32)}"]
    if include_v2:
        keys.append(f"v2:{_encoded(b'b' * 32)}")
    return ConnectorSecretVault(
        Settings(connector_secret_keys=keys, connector_secret_active_key=active)
    )


def test_authenticated_encryption_detects_tampering_and_binds_connector() -> None:
    vault = _vault()
    encrypted = vault.encrypt("github", "synthetic-provider-token")

    assert vault.decrypt("github", encrypted.ciphertext, encrypted.key_version) == (
        "synthetic-provider-token"
    )
    with pytest.raises(SecretVaultError, match="invalide"):
        vault.decrypt("gitlab", encrypted.ciphertext, encrypted.key_version)
    tampered = encrypted.ciphertext[:-2] + "AA"
    with pytest.raises(SecretVaultError, match="invalide"):
        vault.decrypt("github", tampered, encrypted.key_version)


def test_invalid_or_missing_vault_configuration_is_rejected() -> None:
    assert not ConnectorSecretVault(Settings()).configured
    with pytest.raises(SecretVaultError, match="AES-256"):
        ConnectorSecretVault(
            Settings(
                connector_secret_keys=[f"v1:{_encoded(b'short')}"],
                connector_secret_active_key="v1",  # noqa: S106
            )
        )
    with pytest.raises(SecretVaultError, match="active"):
        ConnectorSecretVault(
            Settings(
                connector_secret_keys=[f"v1:{_encoded(b'a' * 32)}"],
                connector_secret_active_key="v2",  # noqa: S106
            )
        )


def test_admin_can_store_rotate_and_delete_without_secret_disclosure(
    authenticated: tuple[TestClient, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, csrf = authenticated
    secret = "synthetic-provider-token-never-returned"
    monkeypatch.setattr(admin_api, "_vault", _vault)

    stored = client.put(
        "/api/v1/admin/connector-secrets/github",
        headers={"X-CSRF-Token": csrf},
        json={"value": secret},
    )
    assert stored.status_code == 200
    assert stored.json()["configured"] is True
    assert stored.json()["key_version"] == "v1"
    assert secret not in stored.text

    listing = client.get("/api/v1/admin/connector-secrets")
    assert listing.status_code == 200
    assert next(
        item for item in listing.json() if item["connector_id"] == "github"
    )["configured"] is True
    assert secret not in listing.text

    rotated_vault = _vault(active="v2", include_v2=True)
    monkeypatch.setattr(admin_api, "_vault", lambda: rotated_vault)
    rotated = client.post(
        "/api/v1/admin/connector-secrets/rotate",
        headers={"X-CSRF-Token": csrf},
    )
    assert rotated.status_code == 200
    assert rotated.json() == {"rotated": 1, "active_key_version": "v2"}
    assert secret not in rotated.text

    deleted = client.delete(
        "/api/v1/admin/connector-secrets/github",
        headers={"X-CSRF-Token": csrf},
    )
    assert deleted.status_code == 204
    statuses = client.get("/api/v1/admin/connector-secrets").json()
    assert next(
        item for item in statuses if item["connector_id"] == "github"
    )["configured"] is False


def test_admin_can_configure_optional_brave_secret(
    authenticated: tuple[TestClient, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, csrf = authenticated
    secret = "synthetic-brave-token-never-returned"
    monkeypatch.setattr(admin_api, "_vault", _vault)

    stored = client.put(
        "/api/v1/admin/connector-secrets/brave",
        headers={"X-CSRF-Token": csrf},
        json={"value": secret},
    )
    assert stored.status_code == 200
    assert stored.json()["configured"] is True
    assert secret not in stored.text


def test_secret_mutations_require_csrf_and_known_connector(
    authenticated: tuple[TestClient, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, csrf = authenticated
    monkeypatch.setattr(admin_api, "_vault", _vault)
    assert (
        client.put(
            "/api/v1/admin/connector-secrets/github", json={"value": "synthetic"}
        ).status_code
        == 403
    )
    assert (
        client.put(
            "/api/v1/admin/connector-secrets/unknown",
            headers={"X-CSRF-Token": csrf},
            json={"value": "synthetic"},
        ).status_code
        == 404
    )
