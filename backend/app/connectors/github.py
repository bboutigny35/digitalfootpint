"""Connecteur minimal vers les profils publics de l'API REST GitHub."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from urllib.parse import quote

import httpx

from app.connectors.base import (
    CandidateResult,
    Connector,
    ConnectorMetadata,
    IdentifierType,
    IdentitySnapshot,
)


class GitHubConnectorError(RuntimeError):
    """Erreur fournisseur explicite ne contenant ni jeton ni donnée sensible."""


class GitHubConnector(Connector):
    metadata = ConnectorMetadata(
        identifier="github",
        version="1.0",
        capabilities=("public_profiles",),
        accepted_identifiers=(IdentifierType.PSEUDONYM,),
        requires_api_key=False,
        rate_limit_per_minute=10,
    )

    def __init__(
        self,
        token: str | None = None,
        *,
        client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 10.0,
        before_request: Callable[[], Awaitable[None]] | None = None,
        quota_exhausted: Callable[[datetime], Awaitable[None]] | None = None,
    ) -> None:
        self._token = token
        self._client = client
        self._timeout = httpx.Timeout(timeout_seconds)
        self._before_request = before_request
        self._quota_exhausted = quota_exhausted

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
            "User-Agent": "DigitalFootprint/0.1",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def search(self, identity: IdentitySnapshot) -> list[CandidateResult]:
        # Une consultation exacte par pseudonyme évite une recherche large et ses faux positifs.
        pseudonyms = tuple(
            dict.fromkeys(value.strip() for value in identity.pseudonyms if value.strip())
        )
        results: list[CandidateResult] = []
        owned_client = self._client is None
        client = self._client or httpx.AsyncClient(
            base_url="https://api.github.com",
            headers=self._headers(),
            timeout=self._timeout,
            follow_redirects=False,
        )
        try:
            for pseudonym in pseudonyms[:10]:
                if self._before_request is not None:
                    await self._before_request()
                try:
                    response = await client.get(
                        f"/users/{quote(pseudonym, safe='')}",
                        headers=self._headers() if self._client is not None else None,
                        timeout=self._timeout,
                        follow_redirects=False,
                    )
                except httpx.HTTPError as exc:
                    raise GitHubConnectorError("API GitHub indisponible") from exc
                if (
                    self._quota_exhausted is not None
                    and response.headers.get("x-ratelimit-remaining") == "0"
                ):
                    reset = response.headers.get("x-ratelimit-reset", "")
                    if reset.isdigit():
                        await self._quota_exhausted(datetime.fromtimestamp(int(reset), UTC))
                if response.status_code == 404:
                    continue
                if response.status_code in {403, 429}:
                    raise GitHubConnectorError("Limite de requêtes GitHub atteinte")
                if response.status_code != 200:
                    raise GitHubConnectorError(
                        f"Réponse GitHub inattendue ({response.status_code})"
                    )
                payload = response.json()
                login = payload.get("login") if isinstance(payload, dict) else None
                if not isinstance(login, str) or login.casefold() != pseudonym.casefold():
                    raise GitHubConnectorError("Réponse GitHub invalide")
                account_type = payload.get("type", "compte")
                results.append(
                    CandidateResult(
                        url=f"https://github.com/{quote(login, safe='')}",
                        title=f"Profil GitHub public de {login}",
                        snippet=f"Type de compte public déclaré par GitHub: {account_type}.",
                        match_type="pseudonym",
                        signals={"exact_pseudonym": True},
                    )
                )
        finally:
            if owned_client:
                await client.aclose()
        return results
