import asyncio

import httpx
import pytest

from app.connectors.base import IdentitySnapshot
from app.connectors.bluesky import (
    BLUESKY_ENDPOINT,
    BlueskyConnector,
    BlueskyConnectorError,
)


def _identity(*pseudonyms: str) -> IdentitySnapshot:
    return IdentitySnapshot(
        first_name="Synthetic",
        last_name="Person",
        pseudonyms=pseudonyms,
        emails=("private@example.test",),
    )


def test_bluesky_resolves_only_exact_handle_shaped_pseudonyms() -> None:
    seen_queries: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).startswith(BLUESKY_ENDPOINT)
        assert request.headers["user-agent"] == "DigitalFootprint/0.1"
        assert "private@example.test" not in str(request.url)
        handle = request.url.params["handle"]
        seen_queries.append(handle)
        if handle == "missing.bsky.social":
            return httpx.Response(404, json={"error": "HandleNotFound"})
        return httpx.Response(200, json={"did": "did:plc:synthetic"})

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            results = await BlueskyConnector(client=client).search(
                _identity(
                    "@alice.bsky.social",
                    "alice.bsky.social",
                    "not-a-handle",
                    "missing.bsky.social",
                )
            )
        assert [result.url for result in results] == ["https://bsky.app/profile/alice.bsky.social"]
        assert results[0].signals == {"exact_pseudonym": True}

    asyncio.run(run())
    assert seen_queries == ["alice.bsky.social", "missing.bsky.social"]


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (httpx.Response(302, headers={"location": "https://example.test"}), "Redirection"),
        (httpx.Response(429), "Limite"),
        (httpx.Response(200, json={"did": "invalid"}), "invalide"),
    ],
)
def test_bluesky_rejects_non_conclusive_responses(
    response: httpx.Response,
    message: str,
) -> None:
    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _request: response)
        ) as client:
            with pytest.raises(BlueskyConnectorError, match=message):
                await BlueskyConnector(client=client).search(_identity("alice.bsky.social"))

    asyncio.run(run())
