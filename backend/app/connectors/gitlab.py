"""Connecteur public minimal vers le statut de profil de GitLab.com."""

from __future__ import annotations

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


class GitLabConnectorError(RuntimeError):
    """Erreur fournisseur réduite et dépourvue du contenu distant."""


class GitLabConnector(Connector):
    metadata = ConnectorMetadata(
        identifier="gitlab",
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
        # Une requête exacte de statut par pseudo ; aucun nom ou e-mail n'est envoyé.
        pseudonyms = tuple(
            dict.fromkeys(value.strip() for value in identity.pseudonyms if value.strip())
        )
        results: list[CandidateResult] = []
        owned_client = self._client is None
        client = self._client or httpx.AsyncClient(
            base_url="https://gitlab.com/api/v4",
            headers={"Accept": "application/json", "User-Agent": "DigitalFootprint/0.1"},
            timeout=self._timeout,
            follow_redirects=False,
        )
        try:
            for pseudonym in pseudonyms[:10]:
                if self._before_request is not None:
                    await self._before_request()
                try:
                    response = await client.get(
                        f"/users/{quote(pseudonym, safe='')}/status",
                        headers={"Accept": "application/json"},
                        timeout=self._timeout,
                        follow_redirects=False,
                    )
                except httpx.HTTPError as exc:
                    raise GitLabConnectorError("API GitLab indisponible") from exc

                if response.status_code == 404:
                    continue
                if response.status_code in {403, 429}:
                    raise GitLabConnectorError("Limite ou accès GitLab atteint")
                if response.status_code != 200:
                    raise GitLabConnectorError(
                        f"Réponse GitLab inattendue ({response.status_code})"
                    )
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise GitLabConnectorError("Réponse GitLab invalide") from exc
                if not isinstance(payload, dict):
                    raise GitLabConnectorError("Réponse GitLab invalide")

                results.append(
                    CandidateResult(
                        url=f"https://gitlab.com/{quote(pseudonym, safe='')}",
                        title=f"Profil GitLab public correspondant à {pseudonym}",
                        snippet=(
                            "Le point de terminaison public GitLab a répondu pour ce pseudonyme."
                        ),
                        match_type="pseudonym",
                        signals={"exact_pseudonym": True},
                    )
                )
        finally:
            if owned_client:
                await client.aclose()
        return results
