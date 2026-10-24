"""Consultation limitée des captures publiques CDX pour les domaines du profil."""

from __future__ import annotations

import ipaddress
from collections.abc import Awaitable, Callable
from datetime import datetime
from urllib.parse import quote, urlsplit

import httpx

from app.connectors.base import (
    CandidateResult,
    Connector,
    ConnectorMetadata,
    IdentifierType,
    IdentitySnapshot,
)

CDX_ENDPOINT = "https://web.archive.org/cdx/search/cdx"
MAX_DOMAINS = 10
MAX_CAPTURES_PER_DOMAIN = 20


class WaybackConnectorError(RuntimeError):
    """Erreur CDX ne contenant ni corps distant ni donnée du profil."""


def _valid_hostname(value: str) -> str | None:
    hostname = value.strip().rstrip(".").lower()
    if not hostname or len(hostname) > 253:
        return None
    try:
        ipaddress.ip_address(hostname)
        return None
    except ValueError:
        pass
    try:
        hostname = hostname.encode("idna").decode("ascii")
    except UnicodeError:
        return None
    labels = hostname.split(".")
    if len(labels) < 2 or any(
        not label
        or len(label) > 63
        or label.startswith("-")
        or label.endswith("-")
        or not all(char.isalnum() or char == "-" for char in label)
        for label in labels
    ):
        return None
    if labels[-1] in {"localhost", "local", "internal", "home"}:
        return None
    return hostname


def _profile_domains(identity: IdentitySnapshot) -> tuple[str, ...]:
    domains: list[str] = []
    for raw_domain in identity.domains:
        if "://" in raw_domain or "/" in raw_domain or "@" in raw_domain:
            continue
        domain = _valid_hostname(raw_domain)
        if domain:
            domains.append(domain)
    for website in identity.websites:
        try:
            parsed = urlsplit(website)
            if (
                parsed.scheme.lower() not in {"http", "https"}
                or parsed.username is not None
                or parsed.password is not None
            ):
                continue
            if parsed.password or parsed.port not in {None, 80, 443}:
                continue
            domain = _valid_hostname(parsed.hostname or "")
        except ValueError:
            continue
        if domain:
            domains.append(domain)
    unique_domains = tuple(dict.fromkeys(domains))
    root_domains = tuple(
        domain
        for domain in unique_domains
        if not any(
            domain != candidate and domain.endswith(f".{candidate}") for candidate in unique_domains
        )
    )
    return root_domains[:MAX_DOMAINS]


def _is_domain_capture(original: str, domain: str) -> bool:
    try:
        parsed = urlsplit(original)
        if (
            parsed.scheme.lower() not in {"http", "https"}
            or parsed.username is not None
            or parsed.password is not None
        ):
            return False
        hostname = _valid_hostname(parsed.hostname or "")
        return bool(hostname and (hostname == domain or hostname.endswith(f".{domain}")))
    except ValueError:
        return False


class WaybackConnector(Connector):
    metadata = ConnectorMetadata(
        identifier="wayback",
        version="1.0",
        capabilities=("domain_archives",),
        accepted_identifiers=(IdentifierType.DOMAIN,),
        requires_api_key=False,
        rate_limit_per_minute=5,
    )

    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 15.0,
        before_request: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self._client = client
        self._timeout = httpx.Timeout(timeout_seconds)
        self._before_request = before_request

    async def search(self, identity: IdentitySnapshot) -> list[CandidateResult]:
        domains = _profile_domains(identity)
        if not domains:
            return []

        owned_client = self._client is None
        client = self._client or httpx.AsyncClient(
            headers={"Accept": "application/json", "User-Agent": "DigitalFootprint/0.1"},
            timeout=self._timeout,
            follow_redirects=False,
        )
        results: list[CandidateResult] = []
        seen: set[str] = set()
        try:
            for domain in domains:
                if self._before_request is not None:
                    await self._before_request()
                try:
                    response = await client.get(
                        CDX_ENDPOINT,
                        params={
                            "url": domain,
                            "matchType": "domain",
                            "output": "json",
                            "fl": "timestamp,original,statuscode",
                            "filter": "statuscode:200",
                            "collapse": "urlkey",
                            "limit": str(MAX_CAPTURES_PER_DOMAIN),
                        },
                        timeout=self._timeout,
                        follow_redirects=False,
                    )
                except httpx.HTTPError as exc:
                    raise WaybackConnectorError("API Wayback indisponible") from exc
                if response.status_code in {403, 429}:
                    raise WaybackConnectorError("Limite ou accès Wayback atteint")
                if response.status_code != 200:
                    raise WaybackConnectorError(
                        f"Réponse Wayback inattendue ({response.status_code})"
                    )
                try:
                    rows = response.json()
                except ValueError as exc:
                    raise WaybackConnectorError("Réponse Wayback invalide") from exc
                if not isinstance(rows, list) or not rows:
                    raise WaybackConnectorError("Réponse Wayback invalide")
                header = rows[0]
                if not isinstance(header, list) or not all(
                    field in header for field in ("timestamp", "original", "statuscode")
                ):
                    raise WaybackConnectorError("Réponse Wayback invalide")
                timestamp_index = header.index("timestamp")
                original_index = header.index("original")
                status_index = header.index("statuscode")
                for row in rows[1 : MAX_CAPTURES_PER_DOMAIN + 1]:
                    if not isinstance(row, list) or len(row) <= max(
                        timestamp_index, original_index, status_index
                    ):
                        continue
                    timestamp, original, status = (
                        row[timestamp_index],
                        row[original_index],
                        row[status_index],
                    )
                    if not all(isinstance(value, str) for value in (timestamp, original, status)):
                        continue
                    if status != "200" or not _is_domain_capture(original, domain):
                        continue
                    try:
                        capture_date = datetime.strptime(timestamp, "%Y%m%d%H%M%S")
                    except ValueError:
                        continue
                    encoded_original = quote(original, safe=":/?&=%[]@!$'()*+,;~-")
                    snapshot_url = f"https://web.archive.org/web/{timestamp}/{encoded_original}"
                    if snapshot_url in seen:
                        continue
                    seen.add(snapshot_url)
                    results.append(
                        CandidateResult(
                            url=snapshot_url,
                            title=f"Capture Wayback de {domain} — {capture_date:%Y-%m-%d}",
                            snippet=f"Capture archivée du domaine renseigné {domain} (HTTP 200).",
                            match_type="domain_archive",
                            published_at=capture_date.isoformat(),
                            signals={"known_domain": True},
                        )
                    )
        finally:
            if owned_client:
                await client.aclose()
        return results
