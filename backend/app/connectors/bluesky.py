"""Résolution exacte de handles Bluesky via l'API publique AT Protocol."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from urllib.parse import quote

import httpx

from app.connectors.base import (
    CandidateResult,
    Connector,
    ConnectorMetadata,
    IdentifierType,
    IdentitySnapshot,
)

BLUESKY_ENDPOINT = "https://public.api.bsky.app/xrpc/com.atproto.identity.resolveHandle"
MAX_HANDLES_PER_SCAN = 10
_HANDLE_PATTERN = re.compile(
    r"(?=.{3,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?\Z"
)


class BlueskyConnectorError(RuntimeError):
    """Erreur fournisseur contrôlée, sans identifiant ni corps distant."""


def _handles(identity: IdentitySnapshot) -> tuple[str, ...]:
    handles: list[str] = []
    seen: set[str] = set()
    for value in identity.pseudonyms:
        handle = value.strip().casefold().removeprefix("@")
        if handle in seen or _HANDLE_PATTERN.fullmatch(handle) is None:
            continue
        seen.add(handle)
        handles.append(handle)
        if len(handles) == MAX_HANDLES_PER_SCAN:
            break
    return tuple(handles)


class BlueskyConnector(Connector):
    metadata = ConnectorMetadata(
        identifier="bluesky",
        version="1.0",
        capabilities=("public_profiles",),
        accepted_identifiers=(IdentifierType.PSEUDONYM,),
        requires_api_key=False,
        rate_limit_per_minute=10,
        crawl_results=True,
    )

    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 10.0,
        before_request: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self._client = client
        self._timeout = httpx.Timeout(timeout_seconds)
        self._before_request = before_request

    async def search(self, identity: IdentitySnapshot) -> list[CandidateResult]:
        owned_client = self._client is None
        client = self._client or httpx.AsyncClient(
            timeout=self._timeout,
            follow_redirects=False,
        )
        results: list[CandidateResult] = []
        try:
            for handle in _handles(identity):
                if self._before_request is not None:
                    await self._before_request()
                try:
                    response = await client.get(
                        BLUESKY_ENDPOINT,
                        params={"handle": handle},
                        headers={
                            "Accept": "application/json",
                            "User-Agent": "DigitalFootprint/0.1",
                        },
                        timeout=self._timeout,
                        follow_redirects=False,
                    )
                except httpx.HTTPError as exc:
                    raise BlueskyConnectorError("API Bluesky indisponible") from exc
                if response.is_redirect:
                    raise BlueskyConnectorError("Redirection Bluesky refusée")
                if response.status_code in {400, 404}:
                    continue
                if response.status_code == 429:
                    raise BlueskyConnectorError("Limite de requêtes Bluesky atteinte")
                if response.status_code != 200:
                    raise BlueskyConnectorError(
                        f"Réponse Bluesky inattendue ({response.status_code})"
                    )
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise BlueskyConnectorError("Réponse Bluesky invalide") from exc
                did = payload.get("did") if isinstance(payload, dict) else None
                if not isinstance(did, str) or not did.startswith("did:") or len(did) > 2048:
                    raise BlueskyConnectorError("Réponse Bluesky invalide")
                results.append(
                    CandidateResult(
                        url=f"https://bsky.app/profile/{quote(handle, safe='.')}",
                        title=f"Profil Bluesky public de {handle}",
                        snippet="Le handle public a été résolu par l’API AT Protocol.",
                        match_type="pseudonym",
                        signals={"exact_pseudonym": True},
                    )
                )
        finally:
            if owned_client:
                await client.aclose()
        return results
