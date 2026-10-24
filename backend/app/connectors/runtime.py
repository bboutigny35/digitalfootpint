"""Construction du catalogue actif selon l'environnement d'exécution."""

from collections.abc import Awaitable, Callable
from datetime import datetime

from app.connectors.mock import MockConnector
from app.connectors.production import build_production_registry
from app.connectors.registry import ConnectorRegistry
from app.core.config import Settings, get_settings


def build_runtime_registry(
    settings: Settings | None = None,
    *,
    github_request_gate: Callable[[], Awaitable[None]] | None = None,
    github_quota_exhausted: Callable[[datetime], Awaitable[None]] | None = None,
    gitlab_request_gate: Callable[[], Awaitable[None]] | None = None,
    wayback_request_gate: Callable[[], Awaitable[None]] | None = None,
    brave_request_gate: Callable[[], Awaitable[None]] | None = None,
    brave_quota_exhausted: Callable[[datetime], Awaitable[None]] | None = None,
    searxng_request_gate: Callable[[], Awaitable[None]] | None = None,
) -> ConnectorRegistry:
    """Ajoute le connecteur hermétique uniquement à l'environnement de test."""
    configuration = settings or get_settings()
    production = build_production_registry(
        configuration,
        github_request_gate=github_request_gate,
        github_quota_exhausted=github_quota_exhausted,
        gitlab_request_gate=gitlab_request_gate,
        wayback_request_gate=wayback_request_gate,
        brave_request_gate=brave_request_gate,
        brave_quota_exhausted=brave_quota_exhausted,
        searxng_request_gate=searxng_request_gate,
    )
    connectors = list(production.all())
    if configuration.environment == "test":
        connectors.append(MockConnector())
    return ConnectorRegistry(connectors)
