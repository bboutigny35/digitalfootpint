import asyncio
from datetime import UTC, datetime

import httpx
import pytest

from app.connectors.base import IdentitySnapshot
from app.connectors.github import GitHubConnector, GitHubConnectorError


def identity(*pseudonyms: str) -> IdentitySnapshot:
    return IdentitySnapshot(first_name="Test", last_name="Synthétique", pseudonyms=pseudonyms)


def test_github_connector_uses_exact_public_profile_and_keeps_token_out_of_url() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"login": "octocat", "type": "User"})

    async def run() -> list[object]:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="https://api.github.com"
        ) as client:
            connector = GitHubConnector("synthetic-token", client=client)
            return await connector.search(identity("octocat"))

    results = asyncio.run(run())
    assert len(results) == 1
    assert results[0].url == "https://github.com/octocat"
    assert requests[0].url == "https://api.github.com/users/octocat"
    assert requests[0].headers["Authorization"] == "Bearer synthetic-token"
    assert "synthetic-token" not in str(requests[0].url)


def test_github_connector_skips_missing_profiles_and_deduplicates() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(404)

    async def run() -> list[object]:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="https://api.github.com"
        ) as client:
            return await GitHubConnector(client=client).search(identity("absent", "absent", ""))

    assert asyncio.run(run()) == []
    assert calls == 1


def test_github_connector_reports_rate_limit_without_leaking_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="secret-provider-message")

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="https://api.github.com"
        ) as client:
            await GitHubConnector(client=client).search(identity("octocat"))

    with pytest.raises(GitHubConnectorError, match="Limite") as caught:
        asyncio.run(run())
    assert "secret-provider-message" not in str(caught.value)


def test_github_connector_uses_gate_before_every_provider_request() -> None:
    gate_calls = 0

    async def gate() -> None:
        nonlocal gate_calls
        gate_calls += 1

    def handler(request: httpx.Request) -> httpx.Response:
        login = request.url.path.rsplit("/", 1)[-1]
        return httpx.Response(200, json={"login": login, "type": "User"})

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="https://api.github.com"
        ) as client:
            connector = GitHubConnector(client=client, before_request=gate)
            await connector.search(identity("first", "second"))

    asyncio.run(run())
    assert gate_calls == 2


def test_github_connector_persists_remote_quota_reset() -> None:
    resets: list[datetime] = []

    async def quota_exhausted(reset_at: datetime) -> None:
        resets.append(reset_at)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "2000000000"},
        )

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="https://api.github.com"
        ) as client:
            connector = GitHubConnector(client=client, quota_exhausted=quota_exhausted)
            await connector.search(identity("limited"))

    with pytest.raises(GitHubConnectorError, match="Limite"):
        asyncio.run(run())
    assert resets == [datetime.fromtimestamp(2_000_000_000, UTC)]
