"""Téléchargement Web borné, respectueux de robots.txt et protégé contre les SSRF."""

from __future__ import annotations

import hashlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

from app.security.outbound import SafeHttpClient
from app.workers.rate_limit import wait_for_request_slot

DomainGate = Callable[[str], Awaitable[None]]

USER_AGENT = "DigitalFootprintBot/0.1"
ROBOTS_MAX_BYTES = 256 * 1024
PAGE_MAX_BYTES = 2 * 1024 * 1024
MAX_RETRY_AFTER_SECONDS = 86400
ROBOTS_MIME_TYPES = {"text/plain", "text/html"}
PAGE_MIME_TYPES = {
    "application/xhtml+xml",
    "text/html",
    "text/plain",
}


class WebFetchError(RuntimeError):
    def __init__(self, code: str, *, retry_after_seconds: int | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.retry_after_seconds = retry_after_seconds


@dataclass(frozen=True, slots=True)
class WebFetchResult:
    final_url: str
    http_status: int
    mime_type: str
    content: bytes


def persistent_domain_gate(requests_per_minute: int = 5) -> DomainGate:
    if requests_per_minute < 1:
        raise ValueError("La limite par domaine doit être positive")

    async def wait(domain: str) -> None:
        domain_key = hashlib.sha256(domain.casefold().encode()).hexdigest()
        await wait_for_request_slot(f"crawl-domain:{domain_key}", requests_per_minute)

    return wait


class WebFetcher:
    def __init__(
        self,
        client: SafeHttpClient,
        *,
        domain_gate: DomainGate,
        user_agent: str = USER_AGENT,
        robots_max_bytes: int = ROBOTS_MAX_BYTES,
        page_max_bytes: int = PAGE_MAX_BYTES,
    ) -> None:
        if robots_max_bytes < 1 or page_max_bytes < 1:
            raise ValueError("Les limites de téléchargement doivent être positives")
        self._client = client
        self._domain_gate = domain_gate
        self._user_agent = user_agent
        self._robots_max_bytes = robots_max_bytes
        self._page_max_bytes = page_max_bytes

    async def fetch(self, url: str) -> WebFetchResult:
        robots_url = self._robots_url(url)
        robots_response = await self._client.get_limited(
            robots_url,
            max_bytes=self._robots_max_bytes,
            allowed_mime_types=ROBOTS_MIME_TYPES,
            before_request=self._domain_gate,
            headers={"User-Agent": self._user_agent, "Accept": "text/plain"},
        )
        if robots_response.status_code in {401, 403}:
            raise WebFetchError("robots_denied")
        if robots_response.status_code == 429 or robots_response.status_code >= 500:
            raise WebFetchError(
                "robots_unavailable",
                retry_after_seconds=self._retry_after(robots_response.headers.get("retry-after")),
            )
        if 300 <= robots_response.status_code < 400:
            raise WebFetchError("robots_unavailable")
        if 200 <= robots_response.status_code < 300:
            parser = RobotFileParser()
            parser.set_url(robots_url)
            parser.parse(robots_response.content.decode("utf-8", errors="replace").splitlines())
            if not parser.can_fetch(self._user_agent, url):
                raise WebFetchError("robots_denied")

        response = await self._client.get_limited(
            url,
            max_bytes=self._page_max_bytes,
            allowed_mime_types=PAGE_MIME_TYPES,
            before_request=self._domain_gate,
            headers={
                "User-Agent": self._user_agent,
                "Accept": "text/html, application/xhtml+xml, text/plain;q=0.8",
            },
        )
        if response.status_code == 429:
            raise WebFetchError(
                "rate_limited",
                retry_after_seconds=self._retry_after(response.headers.get("retry-after")),
            )
        if response.status_code >= 500:
            raise WebFetchError("remote_server_error")
        if response.status_code == 204:
            raise WebFetchError("empty_response")
        if not 200 <= response.status_code < 300:
            raise WebFetchError("remote_http_error")
        mime_type = response.headers["content-type"].split(";", 1)[0].strip().lower()
        final_url = str(response.extensions.get("validated_url", url))
        return WebFetchResult(
            final_url=final_url,
            http_status=response.status_code,
            mime_type=mime_type,
            content=response.content,
        )

    @staticmethod
    def _robots_url(url: str) -> str:
        parsed = urlsplit(url)
        return urlunsplit((parsed.scheme, parsed.netloc, "/robots.txt", "", ""))

    @staticmethod
    def _retry_after(value: str | None) -> int | None:
        if value is None or not value.strip().isdigit():
            return None
        return min(max(int(value.strip()), 1), MAX_RETRY_AFTER_SECONDS)
