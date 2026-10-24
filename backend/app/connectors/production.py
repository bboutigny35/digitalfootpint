"""Catalogue unique des connecteurs autorisés en production."""

from collections.abc import Awaitable, Callable
from datetime import datetime

from app.connectors.brave import BraveSearchConnector
from app.connectors.github import GitHubConnector
from app.connectors.gitlab import GitLabConnector
from app.connectors.registry import ConnectorRegistry
from app.connectors.searxng import SearXNGConnector
from app.connectors.wayback import WaybackConnector
from app.core.config import Settings, get_settings


def build_production_registry(
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
    configuration = settings or get_settings()
    return ConnectorRegistry(
        [
            GitHubConnector(
                configuration.github_api_token,
                before_request=github_request_gate,
                quota_exhausted=github_quota_exhausted,
            ),
            BraveSearchConnector(
                configuration.brave_api_token,
                before_request=brave_request_gate,
                quota_exhausted=brave_quota_exhausted,
            ),
            SearXNGConnector(
                configuration.searxng_url,
                before_request=searxng_request_gate,
            ),
            GitLabConnector(before_request=gitlab_request_gate),
            WaybackConnector(before_request=wayback_request_gate),
        ]
    )
