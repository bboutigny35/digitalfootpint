"""Recherche généraliste via l'instance SearXNG administrée localement."""

from __future__ import annotations

import ipaddress
from collections.abc import Awaitable, Callable
from dataclasses import replace
from urllib.parse import urlsplit

import httpx

from app.connectors.base import (
    CandidateResult,
    Connector,
    ConnectorMetadata,
    IdentifierType,
    IdentitySnapshot,
)
from app.connectors.brave import _safe_result

MAX_QUERIES_PER_SCAN = 5
MAX_RESULTS_PER_QUERY = 10


class SearXNGConnectorError(RuntimeError):
    """Erreur générique sans corps de réponse ni donnée de recherche."""


def _queries(identity: IdentitySnapshot) -> tuple[str, ...]:
    terms = [
        " ".join((identity.first_name.strip(), identity.last_name.strip())).strip(),
        *identity.pseudonyms,
    ]
    queries: list[str] = []
    seen: set[str] = set()
    for term in terms:
        normalized = " ".join(term.split())
        if not normalized or len(normalized) > 120:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        escaped = normalized.replace('"', '\\"')
        queries.append(f'"{escaped}"')
        if len(queries) == MAX_QUERIES_PER_SCAN:
            break
    return tuple(queries)


class SearXNGConnector(Connector):
    metadata = ConnectorMetadata(
        identifier="searxng",
        version="1.0",
        capabilities=("web_search",),
        accepted_identifiers=(IdentifierType.NAME, IdentifierType.PSEUDONYM),
        requires_api_key=False,
        rate_limit_per_minute=5,
        crawl_results=True,
    )

    def __init__(
        self,
        endpoint: str | None,
        *,
        client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 20.0,
        before_request: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self._endpoint = endpoint
        self._client = client
        self._timeout = httpx.Timeout(timeout_seconds)
        self._before_request = before_request

    async def search(self, identity: IdentitySnapshot) -> list[CandidateResult]:
        queries = _queries(identity)
        if not queries:
            return []
        if self._endpoint is None:
            raise SearXNGConnectorError("Instance SearXNG locale non configurée")

        # La destination est une valeur d'administration restreinte à deux URL
        # locales fixes ; le client n'accepte ni redirection ni URL de résultat.
        endpoint = urlsplit(self._endpoint)
        if self._endpoint not in {
            "http://127.0.0.1:8888/search",
            "http://searxng:8080/search",
        } or endpoint.scheme != "http":
            raise SearXNGConnectorError("Configuration SearXNG refusée")

        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(
            timeout=self._timeout,
            follow_redirects=False,
        )
        results: list[CandidateResult] = []
        seen_urls: set[str] = set()
        try:
            for query in queries:
                if self._before_request is not None:
                    await self._before_request()
                try:
                    response = await client.post(
                        self._endpoint,
                        data={
                            "q": query,
                            "format": "json",
                            "safesearch": "1",
                            "language": "fr",
                        },
                        headers={"Accept": "application/json"},
                        timeout=self._timeout,
                        follow_redirects=False,
                    )
                except httpx.HTTPError as exc:
                    raise SearXNGConnectorError("Instance SearXNG indisponible") from exc
                if response.is_redirect:
                    raise SearXNGConnectorError("Redirection SearXNG refusée")
                if response.status_code != 200:
                    raise SearXNGConnectorError(
                        f"Réponse SearXNG inattendue ({response.status_code})"
                    )
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise SearXNGConnectorError("Réponse SearXNG invalide") from exc
                if not isinstance(payload, dict) or not isinstance(
                    payload.get("results"), list
                ):
                    raise SearXNGConnectorError("Réponse SearXNG invalide")
                for raw_result in payload["results"][:MAX_RESULTS_PER_QUERY]:
                    if not isinstance(raw_result, dict):
                        continue
                    normalized_result = {
                        "title": raw_result.get("title"),
                        "url": raw_result.get("url"),
                        "description": raw_result.get("content", ""),
                    }
                    raw_url = normalized_result.get("url")
                    if not isinstance(raw_url, str):
                        continue
                    hostname = urlsplit(raw_url).hostname
                    if not hostname or hostname.lower() in {"localhost"}:
                        continue
                    if hostname.lower().endswith((".localhost", ".local")):
                        continue
                    try:
                        address = ipaddress.ip_address(hostname)
                    except ValueError:
                        address = None
                    if address is not None and not address.is_global:
                        continue
                    candidate = _safe_result(normalized_result)
                    if candidate is None or candidate.url in seen_urls:
                        continue
                    published_at = raw_result.get("publishedDate")
                    if isinstance(published_at, str) and published_at.strip():
                        candidate = replace(candidate, published_at=published_at[:80])
                    results.append(candidate)
                    seen_urls.add(candidate.url)
        finally:
            if owns_client:
                await client.aclose()
        return results
