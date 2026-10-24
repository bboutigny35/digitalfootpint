"""Chiffrement authentifié et rotation des secrets de connecteurs."""

import base64
import binascii
import os
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import Settings, get_settings


class SecretVaultError(RuntimeError):
    """Erreur stable qui ne révèle jamais le secret ni le contenu chiffré."""


@dataclass(frozen=True, slots=True)
class EncryptedSecret:
    ciphertext: str
    key_version: str


class ConnectorSecretVault:
    def __init__(self, settings: Settings | None = None) -> None:
        configuration = settings or get_settings()
        self._keys = self._parse_keys(configuration.connector_secret_keys)
        self.active_version = configuration.connector_secret_active_key
        if self.active_version is not None and self.active_version not in self._keys:
            raise SecretVaultError("Version de clé active indisponible")

    @property
    def configured(self) -> bool:
        return bool(self._keys and self.active_version)

    def encrypt(self, connector_id: str, value: str) -> EncryptedSecret:
        if not self.configured or self.active_version is None:
            raise SecretVaultError("Coffre de secrets non configuré")
        nonce = os.urandom(12)
        key = self._keys[self.active_version]
        encrypted = AESGCM(key).encrypt(nonce, value.encode(), self._aad(connector_id))
        payload = base64.urlsafe_b64encode(nonce + encrypted).decode()
        return EncryptedSecret(payload, self.active_version)

    def decrypt(self, connector_id: str, ciphertext: str, key_version: str) -> str:
        key = self._keys.get(key_version)
        if key is None:
            raise SecretVaultError("Clé de déchiffrement indisponible")
        try:
            payload = base64.urlsafe_b64decode(ciphertext.encode())
            if len(payload) < 29:
                raise ValueError
            plaintext = AESGCM(key).decrypt(
                payload[:12], payload[12:], self._aad(connector_id)
            )
            return plaintext.decode()
        except (ValueError, UnicodeDecodeError, InvalidTag, binascii.Error) as exc:
            raise SecretVaultError("Secret chiffré invalide") from exc

    @staticmethod
    def _aad(connector_id: str) -> bytes:
        return f"digitalfootprint:connector-secret:v1:{connector_id}".encode()

    @staticmethod
    def _parse_keys(entries: list[str]) -> dict[str, bytes]:
        keys: dict[str, bytes] = {}
        for entry in entries:
            version, separator, encoded = entry.partition(":")
            if not separator or not version or version in keys:
                raise SecretVaultError("Configuration de clé invalide")
            try:
                key = base64.urlsafe_b64decode(encoded.encode())
            except (ValueError, binascii.Error) as exc:
                raise SecretVaultError("Configuration de clé invalide") from exc
            if len(key) != 32:
                raise SecretVaultError("Une clé AES-256 de 32 octets est requise")
            keys[version] = key
        return keys
