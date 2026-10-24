"""Téléchargement SSRF-safe et borné des documents de découverte Web."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from app.models.entities import WebSource
from app.security.outbound import SafeHttpClient
from app.services.discovery_documents import (
    MAX_DISCOVERY_DOCUMENT_BYTES,
    MAX_DISCOVERY_ITEMS,
    DiscoveryBatch,
    DiscoveryCandidate,
    DiscoveryDocumentError,
    parse_discovery_document,
)
from app.services.normalization import canonicalize_url
from app.services.web_fetcher import DomainGate

DISCOVERY_MIME_TYPES = {
    "application/atom+xml",
    "application/rss+xml",
    "application/xml",
    "text/xml",
}
MAX_DISCOVERY_DOCUMENTS = 20
MAX_SITEMAP_DEPTH = 2
MAX_RETRY_AFTER_SECONDS = 86400
USER_AGENT = "DigitalFootprintBot/0.1"


class DiscoveryFetchError(RuntimeError):
    def __init__(self, code: str, *, retry_after_seconds: int | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.retry_after_seconds = retry_after_seconds


@dataclass(frozen=True, slots=True)
class DiscoveryFetchResult:
    batch: DiscoveryBatch
    fetched_document_count: int


class DiscoveryDocumentFetcher:
    def __init__(self, client: SafeHttpClient, *, domain_gate: DomainGate) -> None:
        self._client = client
        self._domain_gate = domain_gate

    async def fetch(self, source: WebSource) -> DiscoveryFetchResult:
        if source.state != "active":
            raise DiscoveryDocumentError("Source Web inactive")
        if source.access_method not in {"sitemap", "feed"}:
            raise DiscoveryDocumentError("Méthode de découverte non prise en charge")

        async def source_domain_gate(domain: str) -> None:
            if domain.casefold().rstrip(".") != source.domain.casefold().rstrip("."):
                raise DiscoveryFetchError("source_redirect_outside_domain")
            await self._domain_gate(domain)

        pending = [(source.base_url, 0, source.access_method)]
        seen_documents: set[str] = set()
        seen_items: set[str] = set()
        items: list[DiscoveryCandidate] = []
        nested: list[DiscoveryCandidate] = []
        while pending and len(seen_documents) < MAX_DISCOVERY_DOCUMENTS:
            document_url, depth, access_method = pending.pop(0)
            document_key = canonicalize_url(document_url)
            if document_key in seen_documents:
                continue
            seen_documents.add(document_key)
            response = await self._client.get_limited(
                document_url,
                max_bytes=MAX_DISCOVERY_DOCUMENT_BYTES,
                allowed_mime_types=DISCOVERY_MIME_TYPES,
                before_request=source_domain_gate,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": (
                        "application/xml, text/xml, application/rss+xml, application/atom+xml"
                    ),
                },
            )
            final_url = str(response.extensions.get("validated_url", document_url))
            if not _same_domain(final_url, source.domain):
                raise DiscoveryFetchError("source_redirect_outside_domain")
            if response.status_code == 429:
                raise DiscoveryFetchError(
                    "rate_limited",
                    retry_after_seconds=_retry_after(response.headers.get("retry-after")),
                )
            if response.status_code >= 500:
                raise DiscoveryFetchError("remote_server_error")
            if not 200 <= response.status_code < 300 or response.status_code == 204:
                raise DiscoveryFetchError("remote_http_error")
            batch = parse_discovery_document(
                response.content,
                access_method=access_method,
                source_domain=source.domain,
            )
            for candidate in batch.items:
                if candidate.url in seen_items:
                    continue
                seen_items.add(candidate.url)
                items.append(candidate)
                if len(items) >= MAX_DISCOVERY_ITEMS:
                    break
            if access_method == "sitemap" and depth < MAX_SITEMAP_DEPTH:
                for candidate in batch.nested_sitemaps:
                    nested.append(candidate)
                    pending.append((candidate.url, depth + 1, "sitemap"))
            if len(items) >= MAX_DISCOVERY_ITEMS:
                break
        return DiscoveryFetchResult(
            batch=DiscoveryBatch(
                items=tuple(items),
                nested_sitemaps=tuple(nested),
            ),
            fetched_document_count=len(seen_documents),
        )


def _same_domain(url: str, domain: str) -> bool:
    return (urlsplit(url).hostname or "").casefold().rstrip(".") == domain.casefold().rstrip(".")


def _retry_after(value: str | None) -> int | None:
    if value is None or not value.strip().isdigit():
        return None
    return min(max(int(value.strip()), 1), MAX_RETRY_AFTER_SECONDS)
