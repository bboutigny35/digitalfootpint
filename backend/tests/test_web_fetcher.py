import asyncio

import httpx
import pytest

from app.security.outbound import OutboundResponseTypeRejected, SafeHttpClient
from app.services.web_fetcher import WebFetcher, WebFetchError, persistent_domain_gate


async def resolver(_hostname: str, _port: int) -> list[str]:
    return ["93.184.216.34"]


def test_fetcher_honors_robots_redirects_and_domain_gate() -> None:
    gated_domains: list[str] = []

    async def gate(domain: str) -> None:
        gated_domains.append(domain)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(
                200,
                headers={"Content-Type": "text/plain"},
                text="User-agent: *\nAllow: /",
            )
        if request.headers["Host"] == "one.example.test":
            return httpx.Response(302, headers={"Location": "https://two.example.test/profile"})
        return httpx.Response(
            200,
            headers={"Content-Type": "text/html; charset=utf-8"},
            content=b"<html>public profile</html>",
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await WebFetcher(
                SafeHttpClient(client, resolver=resolver), domain_gate=gate
            ).fetch("https://one.example.test/start")
            assert result.final_url == "https://two.example.test/profile"
            assert result.mime_type == "text/html"
            assert result.content == b"<html>public profile</html>"

    asyncio.run(run())
    assert gated_domains == ["one.example.test", "one.example.test", "two.example.test"]


def test_fetcher_does_not_request_page_for_robots_denial() -> None:
    requested_paths: list[str] = []

    async def gate(_domain: str) -> None:
        return None

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        return httpx.Response(
            200,
            headers={"Content-Type": "text/plain"},
            text="User-agent: *\nDisallow: /private",
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await WebFetcher(SafeHttpClient(client, resolver=resolver), domain_gate=gate).fetch(
                "https://example.test/private/profile"
            )

    with pytest.raises(WebFetchError, match="robots_denied"):
        asyncio.run(run())
    assert requested_paths == ["/robots.txt"]


def test_fetcher_rejects_page_mime_before_returning_content() -> None:
    async def gate(_domain: str) -> None:
        return None

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(
            200,
            headers={"Content-Type": "application/zip"},
            content=b"not accepted",
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await WebFetcher(SafeHttpClient(client, resolver=resolver), domain_gate=gate).fetch(
                "https://example.test/archive"
            )

    with pytest.raises(OutboundResponseTypeRejected):
        asyncio.run(run())


def test_fetcher_bounds_retry_after_without_downloading_error_as_page() -> None:
    async def gate(_domain: str) -> None:
        return None

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(429, headers={"Retry-After": "999999"})

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await WebFetcher(SafeHttpClient(client, resolver=resolver), domain_gate=gate).fetch(
                "https://example.test/profile"
            )

    with pytest.raises(WebFetchError) as caught:
        asyncio.run(run())
    assert caught.value.code == "rate_limited"
    assert caught.value.retry_after_seconds == 86400


def test_persistent_domain_gate_hashes_domain_before_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reservations: list[tuple[str, int]] = []

    async def reserve(identifier: str, rate: int, *, should_stop: object | None = None) -> None:
        assert should_stop is None
        reservations.append((identifier, rate))

    monkeypatch.setattr("app.services.web_fetcher.wait_for_request_slot", reserve)
    asyncio.run(persistent_domain_gate(7)("Personal.Example"))
    assert len(reservations) == 1
    identifier, rate = reservations[0]
    assert identifier.startswith("crawl-domain:")
    assert "personal.example" not in identifier
    assert rate == 7
