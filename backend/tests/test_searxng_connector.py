import asyncio
from urllib.parse import parse_qs

import httpx
import pytest

from app.connectors.base import IdentitySnapshot
from app.connectors.searxng import SearXNGConnector, SearXNGConnectorError


def test_searxng_sends_only_name_and_pseudonym_in_post_body() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "Public page",
                        "url": "https://example.test/path?utm_source=searxng",
                        "content": "Public excerpt",
                        "publishedDate": "2026-01-02",
                    },
                    {"title": "Unsafe", "url": "http://127.0.0.1/admin"},
                ]
            },
        )

    async def run() -> list[object]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await SearXNGConnector(
                "http://127.0.0.1:8888/search", client=client
            ).search(
                IdentitySnapshot(
                    first_name="Alice",
                    last_name="Martin",
                    name_variants=("A. Martin",),
                    pseudonyms=("alice_m",),
                    emails=("private@example.test",),
                    domains=("private.example.test",),
                    keywords=("private keyword",),
                )
            )

    results = asyncio.run(run())
    assert len(requests) == 2
    assert all(request.method == "POST" for request in requests)
    assert all(request.url.path == "/search" for request in requests)
    assert all(request.url.query == b"" for request in requests)
    bodies = [parse_qs(request.content.decode())["q"][0] for request in requests]
    assert bodies[0] == '"Alice Martin"'
    assert bodies[1] == '"alice_m"'
    assert all("private@example.test" not in body for body in bodies)
    assert all("private.example.test" not in body for body in bodies)
    assert all("private keyword" not in body for body in bodies)
    assert all("A. Martin" not in body for body in bodies)
    assert len(results) == 1
    assert results[0].url == "https://example.test/path"
    assert results[0].snippet == "Public excerpt"
    assert results[0].published_at == "2026-01-02"


def test_searxng_requires_a_local_instance_and_does_not_fake_results() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"results": []})

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await SearXNGConnector(None, client=client).search(
                IdentitySnapshot(first_name="Alice", last_name="Martin")
            )

    with pytest.raises(SearXNGConnectorError, match="non configurée"):
        asyncio.run(run())
    assert calls == 0


def test_searxng_refuses_redirects_and_hides_remote_response_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            302,
            text="synthetic-private-upstream-body",
            headers={"Location": "http://169.254.169.254/latest/meta-data"},
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await SearXNGConnector(
                "http://127.0.0.1:8888/search", client=client
            ).search(IdentitySnapshot(first_name="Alice", last_name="Martin"))

    with pytest.raises(SearXNGConnectorError, match="Redirection") as caught:
        asyncio.run(run())
    assert "synthetic-private-upstream-body" not in str(caught.value)


def test_searxng_applies_shared_rate_gate_and_limits_queries() -> None:
    gate_calls = 0
    request_count = 0

    async def gate() -> None:
        nonlocal gate_calls
        gate_calls += 1

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(200, json={"results": []})

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await SearXNGConnector(
                "http://127.0.0.1:8888/search", client=client, before_request=gate
            ).search(
                IdentitySnapshot(
                    first_name="Alice",
                    last_name="Martin",
                    pseudonyms=("one", "two", "three", "four", "five"),
                )
            )

    asyncio.run(run())
    assert gate_calls == 5
    assert request_count == 5


def test_searxng_rejects_invalid_response_shape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": "invalid"})

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await SearXNGConnector(
                "http://127.0.0.1:8888/search", client=client
            ).search(IdentitySnapshot(first_name="Alice", last_name="Martin"))

    with pytest.raises(SearXNGConnectorError, match="invalide"):
        asyncio.run(run())
