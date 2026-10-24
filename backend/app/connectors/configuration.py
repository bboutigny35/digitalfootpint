"""Activation persistante des connecteurs connus."""

from sqlalchemy.orm import Session

from app.connectors.registry import ConnectorRegistry
from app.core.config import get_settings
from app.models.entities import ConnectorConfiguration, ConnectorSecret


def connector_is_enabled(db: Session, connector_id: str) -> bool:
    configuration = db.get(ConnectorConfiguration, connector_id)
    return configuration is None or configuration.enabled


def connector_is_ready(db: Session, connector_id: str, requires_api_key: bool) -> bool:
    """Indique si un connecteur à clé possède un secret configuré, sans le déchiffrer."""
    if connector_id == "searxng":
        return bool(get_settings().searxng_url)
    if not requires_api_key:
        return True
    settings = get_settings()
    setting_name = {"brave": "brave_api_token", "github": "github_api_token"}.get(connector_id)
    if setting_name and getattr(settings, setting_name, None):
        return True
    return db.get(ConnectorSecret, connector_id) is not None


def enabled_registry(db: Session, registry: ConnectorRegistry) -> ConnectorRegistry:
    return ConnectorRegistry(
        [
            connector
            for connector in registry.all()
            if connector_is_enabled(db, connector.metadata.identifier)
        ]
    )
