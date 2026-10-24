import asyncio

import httpx
import pytest

from app.security.outbound import SafeHttpClient, UnsafeOutboundUrl, validate_public_url


async def resolver(_hostname: str, _port: int) -> list[str]:
    return ["93.184.216.34"]


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/admin",
        "http://[::1]/",
        "http://10.0.0.1/",
        "http://172.16.0.1/",
        "http://192.168.1.1/",
        "http://169.254.169.254/latest/meta-data/",
        "http://100.64.0.1/",
        "ftp://example.test/file",
        "https://user:password@example.test/",
        "https://example.test:8443/",
    ],
)
def test_private_or_unsafe_destinations_are_rejected(url: str) -> None:
    with pytest.raises(UnsafeOutboundUrl):
        asyncio.run(validate_public_url(url, resolver))


def test_all_dns_answers_must_be_public() -> None:
    async def mixed_resolver(_hostname: str, _port: int) -> list[str]:
        return ["93.184.216.34", "127.0.0.1"]

    with pytest.raises(UnsafeOutboundUrl, match="non publique"):
        asyncio.run(validate_public_url("https://example.test/", mixed_resolver))


def test_redirect_is_revalidated_and_private_target_is_never_requested() -> None:
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return httpx.Response(302, headers={"Location": "http://169.254.169.254/secret"})

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            safe_client = SafeHttpClient(client, resolver=resolver)
            await safe_client.get("https://public.example.test/start")

    with pytest.raises(UnsafeOutboundUrl):
        asyncio.run(run())
    assert requested == ["https://93.184.216.34/start"]


def test_authorization_is_not_forwarded_to_another_origin() -> None:
    authorization_headers: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        authorization_headers.append(request.headers.get("Authorization"))
        if request.headers["Host"] == "one.example.test":
            return httpx.Response(302, headers={"Location": "https://two.example.test/end"})
        return httpx.Response(200)

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            safe_client = SafeHttpClient(client, resolver=resolver)
            response = await safe_client.get(
                "https://one.example.test/start", headers={"Authorization": "Bearer synthetic"}
            )
            assert response.status_code == 200

    asyncio.run(run())
    assert authorization_headers == ["Bearer synthetic", None]


def test_connection_is_pinned_to_validated_address_with_tls_hostname() -> None:
    requests: list[httpx.Request] = []
    resolution_count = 0

    async def rebinding_resolver(_hostname: str, _port: int) -> list[str]:
        nonlocal resolution_count
        resolution_count += 1
        return ["93.184.216.34"] if resolution_count == 1 else ["127.0.0.1"]

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200)

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            response = await SafeHttpClient(client, resolver=rebinding_resolver).get(
                "https://public.example.test/resource"
            )
            assert response.status_code == 200

    asyncio.run(run())
    assert resolution_count == 1
    assert len(requests) == 1
    assert str(requests[0].url) == "https://93.184.216.34/resource"
    assert requests[0].headers["Host"] == "public.example.test"
    assert requests[0].headers["Connection"] == "close"
    assert requests[0].extensions["sni_hostname"] == "public.example.test"
