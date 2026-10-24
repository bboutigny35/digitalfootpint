import asyncio
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.connectors.base import IdentitySnapshot
from app.connectors.brave import BraveSearchConnector, BraveSearchConnectorError


def test_brave_uses_official_api_and_sends_key_only_in_header() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {
                            "title": "Public result",
                            "url": "https://example.test/page?utm_source=brave",
                            "description": "Public excerpt",
                        },
                        {"title": "Unsafe", "url": "javascript:alert(1)"},
                    ]
                }
            },
        )

    async def run() -> list[object]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await BraveSearchConnector("synthetic-brave-key", client=client).search(
                IdentitySnapshot(
                    first_name="Alice",
                    last_name="Martin",
                    pseudonyms=("alice_m",),
                    emails=("private@example.test",),
                    keywords=("private keyword",),
                )
            )

    results = asyncio.run(run())
    assert len(requests) == 2
    assert requests[0].url.host == "api.search.brave.com"
    assert requests[0].url.path == "/res/v1/web/search"
    assert requests[0].headers["X-Subscription-Token"] == "synthetic-brave-key"
    assert "synthetic-brave-key" not in str(requests[0].url)
    sent_queries = [request.url.params["q"] for request in requests]
    assert sent_queries == ['"Alice Martin"', '"alice_m"']
    assert all("private@example.test" not in query for query in sent_queries)
    assert all("private keyword" not in query for query in sent_queries)
    assert len(results) == 1
    assert results[0].url == "https://example.test/page"


def test_brave_does_not_fake_results_without_an_api_key() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"web": {"results": []}})

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await BraveSearchConnector(None, client=client).search(
                IdentitySnapshot(first_name="Alice", last_name="Martin")
            )

    with pytest.raises(BraveSearchConnectorError, match="non configurée"):
        asyncio.run(run())
    assert calls == 0


def test_brave_applies_persistent_gate_and_caps_query_count() -> None:
    gate_calls = 0
    queries: list[str] = []

    async def gate() -> None:
        nonlocal gate_calls
        gate_calls += 1

    def handler(request: httpx.Request) -> httpx.Response:
        queries.append(request.url.params["q"])
        return httpx.Response(200, json={"web": {"results": []}})

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await BraveSearchConnector(
                "synthetic-key", client=client, before_request=gate
            ).search(
                IdentitySnapshot(
                    first_name="Alice",
                    last_name="Martin",
                    name_variants=("A. Martin", "Alice M."),
                    pseudonyms=("one", "two", "three"),
                )
            )

    asyncio.run(run())
    assert gate_calls == 5
    assert len(queries) == 5


def test_brave_persists_provider_reset_on_429_without_leaking_body() -> None:
    resume_times: list[datetime] = []

    async def quota_exhausted(resume_at: datetime) -> None:
        resume_times.append(resume_at)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            text="synthetic-provider-error-body",
            headers={"X-RateLimit-Remaining": "0, 0", "X-RateLimit-Reset": "1, 3600"},
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await BraveSearchConnector(
                "synthetic-key", client=client, quota_exhausted=quota_exhausted
            ).search(IdentitySnapshot(first_name="Alice", last_name="Martin"))

    started = datetime.now(UTC)
    with pytest.raises(BraveSearchConnectorError, match="Quota") as caught:
        asyncio.run(run())
    assert "synthetic-provider-error-body" not in str(caught.value)
    assert len(resume_times) == 1
    assert started + timedelta(seconds=3590) < resume_times[0] < started + timedelta(seconds=3610)


def test_brave_rejects_invalid_response_shape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"web": {"results": "invalid"}})

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await BraveSearchConnector("synthetic-key", client=client).search(
                IdentitySnapshot(first_name="Alice", last_name="Martin")
            )

    with pytest.raises(BraveSearchConnectorError, match="invalide"):
        asyncio.run(run())
