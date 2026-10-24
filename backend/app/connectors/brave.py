"""Recherche Web facultative via l'API officielle Brave Search."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

import httpx

from app.connectors.base import (
    CandidateResult,
    Connector,
    ConnectorMetadata,
    IdentifierType,
    IdentitySnapshot,
)
from app.services.normalization import canonicalize_url

BRAVE_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
MAX_QUERIES_PER_SCAN = 5
MAX_RESULTS_PER_QUERY = 10


class BraveSearchConnectorError(RuntimeError):
    """Erreur du fournisseur Brave ne contenant ni clé ni corps distant."""


def _queries(identity: IdentitySnapshot) -> tuple[str, ...]:
    terms = [
        " ".join((identity.first_name.strip(), identity.last_name.strip())).strip(),
        *identity.name_variants,
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


def _safe_result(result: object) -> CandidateResult | None:
    if not isinstance(result, dict):
        return None
    title = result.get("title")
    raw_url = result.get("url")
    description = result.get("description", "")
    if not isinstance(title, str) or not isinstance(raw_url, str):
        return None
    if not isinstance(description, str):
        description = ""
    try:
        parsed = urlsplit(raw_url)
        if (
            parsed.scheme.lower() not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
        ):
            return None
        canonical_url = canonicalize_url(raw_url)
    except ValueError:
        return None
    return CandidateResult(
        url=canonical_url,
        title=" ".join(title.split())[:300],
        snippet=" ".join(description.split())[:700],
        match_type="web_search",
        signals={"provider_indexed": True},
    )


class BraveSearchConnector(Connector):
    metadata = ConnectorMetadata(
        identifier="brave",
        version="1.0",
        capabilities=("web_search",),
        accepted_identifiers=(IdentifierType.NAME, IdentifierType.PSEUDONYM),
        requires_api_key=True,
        rate_limit_per_minute=5,
        crawl_results=True,
    )

    def __init__(
        self,
        token: str | None,
        *,
        client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 15.0,
        before_request: Callable[[], Awaitable[None]] | None = None,
        quota_exhausted: Callable[[datetime], Awaitable[None]] | None = None,
    ) -> None:
        self._token = token
        self._client = client
        self._timeout = httpx.Timeout(timeout_seconds)
        self._before_request = before_request
        self._quota_exhausted = quota_exhausted

    async def search(self, identity: IdentitySnapshot) -> list[CandidateResult]:
        queries = _queries(identity)
        if not queries:
            return []
        if not self._token:
            raise BraveSearchConnectorError("Clé API Brave non configurée")

        owned_client = self._client is None
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
                    response = await client.get(
                        BRAVE_ENDPOINT,
                        params={
                            "q": query,
                            "count": str(MAX_RESULTS_PER_QUERY),
                            "safesearch": "moderate",
                        },
                        headers={
                            "Accept": "application/json",
                            "X-Subscription-Token": self._token,
                        },
                        timeout=self._timeout,
                        follow_redirects=False,
                    )
                except httpx.HTTPError as exc:
                    raise BraveSearchConnectorError("API Brave indisponible") from exc
                if response.status_code == 429:
                    await self._defer_from_rate_headers(response)
                    raise BraveSearchConnectorError("Quota ou limite Brave atteint")
                if response.status_code in {401, 403}:
                    raise BraveSearchConnectorError("Clé API Brave refusée")
                if response.status_code != 200:
                    raise BraveSearchConnectorError(
                        f"Réponse Brave inattendue ({response.status_code})"
                    )
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise BraveSearchConnectorError("Réponse Brave invalide") from exc
                if not isinstance(payload, dict):
                    raise BraveSearchConnectorError("Réponse Brave invalide")
                web = payload.get("web", {})
                if not isinstance(web, dict):
                    raise BraveSearchConnectorError("Réponse Brave invalide")
                provider_results = web.get("results", [])
                if not isinstance(provider_results, list):
                    raise BraveSearchConnectorError("Réponse Brave invalide")
                for raw_result in provider_results[:MAX_RESULTS_PER_QUERY]:
                    candidate = _safe_result(raw_result)
                    if candidate is None or candidate.url in seen_urls:
                        continue
                    seen_urls.add(candidate.url)
                    results.append(candidate)
        finally:
            if owned_client:
                await client.aclose()
        return results

    async def _defer_from_rate_headers(self, response: httpx.Response) -> None:
        if self._quota_exhausted is None:
            return
        remaining = response.headers.get("x-ratelimit-remaining", "").split(",")
        resets = response.headers.get("x-ratelimit-reset", "").split(",")
        delays = [
            int(reset.strip())
            for left, reset in zip(remaining, resets, strict=False)
            if left.strip().isdigit()
            and int(left.strip()) <= 0
            and reset.strip().isdigit()
        ]
        if delays:
            await self._quota_exhausted(datetime.now(UTC) + timedelta(seconds=max(delays)))
