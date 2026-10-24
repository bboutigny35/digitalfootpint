import asyncio

import httpx
import pytest

from app.connectors.base import IdentitySnapshot
from app.connectors.wayback import WaybackConnector, WaybackConnectorError


def identity(*domains: str, websites: tuple[str, ...] = ()) -> IdentitySnapshot:
    return IdentitySnapshot(
        first_name="Test",
        last_name="Synthétique",
        domains=domains,
        websites=websites,
    )


def test_wayback_queries_only_known_domains_and_minimizes_cdx_results() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json=[
                ["timestamp", "original", "statuscode"],
                ["20240102030405", "https://www.example.test/about", "200"],
                ["20240102030406", "https://unrelated.test/leak", "200"],
                ["invalid", "https://example.test/bad-date", "200"],
            ],
        )

    async def run() -> list[object]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await WaybackConnector(client=client).search(
                identity("example.test", websites=("https://www.example.test/profile",))
            )

    results = asyncio.run(run())
    assert len(requests) == 1
    assert requests[0].url.host == "web.archive.org"
    assert requests[0].url.path == "/cdx/search/cdx"
    assert requests[0].url.params["url"] == "example.test"
    assert requests[0].url.params["matchType"] == "domain"
    assert len(results) == 1
    assert results[0].url == (
        "https://web.archive.org/web/20240102030405/https://www.example.test/about"
    )
    assert results[0].published_at == "2024-01-02T03:04:05"
    assert "unrelated.test" not in results[0].snippet


def test_wayback_deduplicates_and_limits_domains_and_captures() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=[["timestamp", "original", "statuscode"]])

    async def run() -> list[object]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            domains = tuple(["example.test", "example.test", *[f"site{i}.test" for i in range(12)]])
            return await WaybackConnector(client=client).search(identity(*domains))

    assert asyncio.run(run()) == []
    assert len(requests) == 10
    assert all(request.url.params["limit"] == "20" for request in requests)


def test_wayback_ignores_invalid_domain_inputs_and_private_profile_data() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=[["timestamp", "original", "statuscode"]])

    async def run() -> list[object]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await WaybackConnector(client=client).search(
                IdentitySnapshot(
                    first_name="Secret Name",
                    last_name="Private",
                    emails=("private@example.test",),
                    pseudonyms=("private-handle",),
                    domains=(
                        "http://127.0.0.1/path",
                        "127.0.0.1",
                        "user@host.test",
                        "localhost",
                        "example.local",
                    ),
                )
            )

    assert asyncio.run(run()) == []
    assert calls == 0


def test_wayback_uses_persistent_gate_per_domain() -> None:
    gate_calls = 0

    async def gate() -> None:
        nonlocal gate_calls
        gate_calls += 1

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[["timestamp", "original", "statuscode"]])

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await WaybackConnector(client=client, before_request=gate).search(
                identity("one.test", websites=("https://two.test/",))
            )

    asyncio.run(run())
    assert gate_calls == 2


def test_wayback_reduces_rate_limit_error_without_leaking_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="synthetic-provider-secret")

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await WaybackConnector(client=client).search(identity("example.test"))

    with pytest.raises(WaybackConnectorError, match="Limite") as caught:
        asyncio.run(run())
    assert "synthetic-provider-secret" not in str(caught.value)
