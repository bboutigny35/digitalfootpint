import asyncio

import httpx
import pytest

from app.connectors.base import IdentitySnapshot
from app.connectors.gitlab import GitLabConnector, GitLabConnectorError


def identity(*pseudonyms: str) -> IdentitySnapshot:
    return IdentitySnapshot(first_name="Test", last_name="Synthétique", pseudonyms=pseudonyms)


def test_gitlab_connector_uses_public_status_api_and_returns_minimized_result() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"emoji": "", "message": "private status text"})

    async def run() -> list[object]:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="https://gitlab.com/api/v4"
        ) as client:
            return await GitLabConnector(client=client).search(identity("octo-cat"))

    results = asyncio.run(run())
    assert len(results) == 1
    assert results[0].url == "https://gitlab.com/octo-cat"
    assert requests[0].url == "https://gitlab.com/api/v4/users/octo-cat/status"
    assert "private status text" not in results[0].snippet
    assert requests[0].headers["accept"] == "application/json"


def test_gitlab_connector_escapes_path_deduplicates_and_limits_pseudonyms() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(404)

    async def run() -> list[object]:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="https://gitlab.com/api/v4"
        ) as client:
            return await GitLabConnector(client=client).search(
                identity("a/b", "a/b", *[f"user-{index}" for index in range(12)])
            )

    assert asyncio.run(run()) == []
    assert len(requests) == 10
    assert requests[0].url.raw_path == b"/api/v4/users/a%2Fb/status"


def test_gitlab_connector_runs_persistent_gate_before_each_request() -> None:
    gate_calls = 0

    async def gate() -> None:
        nonlocal gate_calls
        gate_calls += 1

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="https://gitlab.com/api/v4"
        ) as client:
            await GitLabConnector(client=client, before_request=gate).search(
                identity("first", "second")
            )

    asyncio.run(run())
    assert gate_calls == 2


def test_gitlab_connector_reduces_errors_without_leaking_provider_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="synthetic-private-provider-response")

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="https://gitlab.com/api/v4"
        ) as client:
            await GitLabConnector(client=client).search(identity("octocat"))

    with pytest.raises(GitLabConnectorError, match="Limite") as caught:
        asyncio.run(run())
    assert "synthetic-private-provider-response" not in str(caught.value)


def test_gitlab_connector_rejects_unexpected_json_shape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=["not", "an", "object"])

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="https://gitlab.com/api/v4"
        ) as client:
            await GitLabConnector(client=client).search(identity("octocat"))

    with pytest.raises(GitLabConnectorError, match="invalide"):
        asyncio.run(run())
