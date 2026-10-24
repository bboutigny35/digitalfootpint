import asyncio

import httpx
import pytest

from app.models.entities import WebSource
from app.security.outbound import SafeHttpClient, UnsafeOutboundUrl
from app.services.discovery_fetcher import (
    DiscoveryDocumentFetcher,
    DiscoveryFetchError,
)


async def resolver(_hostname: str, _port: int) -> list[str]:
    return ["93.184.216.34"]


def active_source(*, access_method: str = "sitemap") -> WebSource:
    return WebSource(
        domain="example.test",
        base_url="https://example.test/root.xml",
        category="public",
        access_method=access_method,
        state="active",
    )


def test_fetcher_recurses_sitemap_indexes_with_bounded_depth_and_quota() -> None:
    requested_paths: list[str] = []
    gated_domains: list[str] = []

    async def gate(domain: str) -> None:
        gated_domains.append(domain)

    documents = {
        "/root.xml": b"""<sitemapindex><sitemap>
          <loc>https://example.test/level-1.xml</loc>
        </sitemap></sitemapindex>""",
        "/level-1.xml": b"""<sitemapindex><sitemap>
          <loc>https://example.test/level-2.xml</loc>
        </sitemap></sitemapindex>""",
        "/level-2.xml": b"""<urlset>
          <url><loc>https://example.test/profile</loc></url>
        </urlset>""",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        return httpx.Response(
            200,
            headers={"Content-Type": "application/xml"},
            content=documents[request.url.path],
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await DiscoveryDocumentFetcher(
                SafeHttpClient(client, resolver=resolver), domain_gate=gate
            ).fetch(active_source())
            assert result.fetched_document_count == 3
            assert [item.url for item in result.batch.items] == ["https://example.test/profile"]

    asyncio.run(run())
    assert requested_paths == ["/root.xml", "/level-1.xml", "/level-2.xml"]
    assert gated_domains == ["example.test", "example.test", "example.test"]


def test_fetcher_refuses_cross_domain_final_redirect() -> None:
    requested_hosts: list[str] = []

    async def gate(_domain: str) -> None:
        return None

    def handler(request: httpx.Request) -> httpx.Response:
        requested_hosts.append(request.headers["Host"])
        if request.headers["Host"] == "example.test":
            return httpx.Response(302, headers={"Location": "https://other.test/feed.xml"})
        return httpx.Response(
            200,
            headers={"Content-Type": "application/rss+xml"},
            content=b"<rss><channel/></rss>",
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await DiscoveryDocumentFetcher(
                SafeHttpClient(client, resolver=resolver), domain_gate=gate
            ).fetch(active_source(access_method="feed"))

    with pytest.raises(DiscoveryFetchError, match="source_redirect_outside_domain"):
        asyncio.run(run())
    assert requested_hosts == ["example.test"]


def test_fetcher_revalidates_private_redirect_before_request() -> None:
    requested: list[str] = []

    async def gate(_domain: str) -> None:
        return None

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return httpx.Response(302, headers={"Location": "http://127.0.0.1/private.xml"})

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await DiscoveryDocumentFetcher(
                SafeHttpClient(client, resolver=resolver), domain_gate=gate
            ).fetch(active_source())

    with pytest.raises(UnsafeOutboundUrl):
        asyncio.run(run())
    assert requested == ["https://93.184.216.34/root.xml"]


def test_fetcher_bounds_retry_after() -> None:
    async def gate(_domain: str) -> None:
        return None

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "999999"})

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await DiscoveryDocumentFetcher(
                SafeHttpClient(client, resolver=resolver), domain_gate=gate
            ).fetch(active_source())

    with pytest.raises(DiscoveryFetchError) as caught:
        asyncio.run(run())
    assert caught.value.code == "rate_limited"
    assert caught.value.retry_after_seconds == 86400
