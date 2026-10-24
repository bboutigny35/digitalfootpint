"""Validation des destinations réseau non fiables contre les SSRF."""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from collections.abc import Awaitable, Callable, Iterable, Mapping
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx

Resolver = Callable[[str, int], Awaitable[Iterable[str]]]


class UnsafeOutboundUrl(ValueError):
    """Destination refusée sans révéler de détails réseau sensibles."""


class OutboundResponseTooLarge(ValueError):
    """Réponse distante interrompue dès que la limite autorisée est dépassée."""


class OutboundResponseTypeRejected(ValueError):
    """Type de contenu distant absent ou non autorisé."""


async def system_resolver(hostname: str, port: int) -> Iterable[str]:
    def resolve() -> set[str]:
        records = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
        return {str(record[4][0]) for record in records}

    try:
        return await asyncio.to_thread(resolve)
    except socket.gaierror as exc:
        raise UnsafeOutboundUrl("Résolution DNS impossible") from exc


def _validate_address(value: str) -> None:
    try:
        address = ipaddress.ip_address(value.split("%", 1)[0])
    except ValueError as exc:
        raise UnsafeOutboundUrl("Adresse DNS invalide") from exc
    if not address.is_global:
        raise UnsafeOutboundUrl("Destination réseau non publique interdite")


async def resolve_public_url(
    url: str, resolver: Resolver = system_resolver
) -> tuple[str, str, int, tuple[str, ...]]:
    """Valide l'URL et retourne toutes les adresses publiques à épingler."""
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise UnsafeOutboundUrl("URL HTTP(S) absolue requise")
    if parsed.username is not None or parsed.password is not None:
        raise UnsafeOutboundUrl("Identifiants intégrés à l'URL interdits")
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        raise UnsafeOutboundUrl("Port invalide") from exc
    if port not in {80, 443}:
        raise UnsafeOutboundUrl("Port sortant interdit")

    hostname = parsed.hostname.rstrip(".").lower()
    try:
        literal = ipaddress.ip_address(hostname.split("%", 1)[0])
    except ValueError:
        addresses = tuple(await resolver(hostname, port))
        if not addresses:
            raise UnsafeOutboundUrl("Résolution DNS vide") from None
        for address in addresses:
            _validate_address(address)
    else:
        addresses = (str(literal),)
        _validate_address(addresses[0])
    return url, hostname, port, addresses


async def validate_public_url(url: str, resolver: Resolver = system_resolver) -> str:
    await resolve_public_url(url, resolver)
    return url


def _pinned_url(url: str, address: str) -> str:
    parsed = urlsplit(url)
    host = f"[{address}]" if ":" in address else address
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"
    return urlunsplit((parsed.scheme, host, parsed.path, parsed.query, parsed.fragment))


def _host_header(hostname: str, scheme: str, port: int) -> str:
    default_port = 443 if scheme == "https" else 80
    return hostname if port == default_port else f"{hostname}:{port}"


class SafeHttpClient:
    """Client qui revalide chaque destination et chaque redirection."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        resolver: Resolver = system_resolver,
        max_redirects: int = 3,
    ) -> None:
        self._client = client
        self._resolver = resolver
        self._max_redirects = max_redirects

    async def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        timeout: float = 10.0,
    ) -> httpx.Response:
        current_url = url
        request_headers = dict(headers or {})
        initial_origin = self._origin(url)
        for redirect_count in range(self._max_redirects + 1):
            _, hostname, port, addresses = await resolve_public_url(current_url, self._resolver)
            if self._origin(current_url) != initial_origin:
                request_headers.pop("Authorization", None)
                request_headers.pop("authorization", None)
            pinned_headers = dict(request_headers)
            parsed = urlsplit(current_url)
            pinned_headers["Host"] = _host_header(hostname, parsed.scheme, port)
            # L'origine technique est l'IP épinglée : interdire sa réutilisation
            # pour un autre nom d'hôte partageant éventuellement cette adresse.
            pinned_headers["Connection"] = "close"
            response: httpx.Response | None = None
            last_connection_error: httpx.ConnectError | httpx.ConnectTimeout | None = None
            for address in addresses:
                try:
                    response = await self._client.get(
                        _pinned_url(current_url, address),
                        headers=pinned_headers,
                        timeout=timeout,
                        follow_redirects=False,
                        extensions={"sni_hostname": hostname},
                    )
                    break
                except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                    last_connection_error = exc
            if response is None:
                if last_connection_error is not None:
                    raise last_connection_error
                raise UnsafeOutboundUrl("Aucune destination publique disponible")
            if response.status_code not in {301, 302, 303, 307, 308}:
                return response
            if redirect_count >= self._max_redirects:
                raise UnsafeOutboundUrl("Trop de redirections")
            location = response.headers.get("location")
            if not location:
                raise UnsafeOutboundUrl("Redirection sans destination")
            current_url = urljoin(current_url, location)
        raise UnsafeOutboundUrl("Redirection refusée")

    async def get_limited(
        self,
        url: str,
        *,
        max_bytes: int,
        allowed_mime_types: set[str] | None = None,
        before_request: Callable[[str], Awaitable[None]] | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float = 10.0,
    ) -> httpx.Response:
        """Télécharge au plus ``max_bytes`` après validation de chaque destination."""
        if max_bytes < 1:
            raise ValueError("La limite de réponse doit être positive")
        current_url = url
        request_headers = dict(headers or {})
        initial_origin = self._origin(url)
        for redirect_count in range(self._max_redirects + 1):
            _, hostname, port, addresses = await resolve_public_url(current_url, self._resolver)
            if before_request is not None:
                await before_request(hostname)
            if self._origin(current_url) != initial_origin:
                request_headers.pop("Authorization", None)
                request_headers.pop("authorization", None)
            pinned_headers = dict(request_headers)
            parsed = urlsplit(current_url)
            pinned_headers["Host"] = _host_header(hostname, parsed.scheme, port)
            pinned_headers["Connection"] = "close"
            response: httpx.Response | None = None
            last_connection_error: httpx.ConnectError | httpx.ConnectTimeout | None = None
            for address in addresses:
                request = self._client.build_request(
                    "GET",
                    _pinned_url(current_url, address),
                    headers=pinned_headers,
                    timeout=timeout,
                    extensions={"sni_hostname": hostname},
                )
                try:
                    response = await self._client.send(request, stream=True, follow_redirects=False)
                    break
                except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                    last_connection_error = exc
            if response is None:
                if last_connection_error is not None:
                    raise last_connection_error
                raise UnsafeOutboundUrl("Aucune destination publique disponible")
            if response.status_code in {301, 302, 303, 307, 308}:
                await response.aclose()
                if redirect_count >= self._max_redirects:
                    raise UnsafeOutboundUrl("Trop de redirections")
                location = response.headers.get("location")
                if not location:
                    raise UnsafeOutboundUrl("Redirection sans destination")
                current_url = urljoin(current_url, location)
                continue
            if (
                allowed_mime_types is not None
                and 200 <= response.status_code < 300
                and response.status_code != 204
            ):
                mime_type = (
                    response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                )
                if mime_type not in allowed_mime_types:
                    await response.aclose()
                    raise OutboundResponseTypeRejected("Type de contenu distant refusé")
            declared_length = response.headers.get("content-length")
            if declared_length is not None:
                try:
                    parsed_length = int(declared_length)
                except ValueError as exc:
                    await response.aclose()
                    raise UnsafeOutboundUrl("Longueur de réponse invalide") from exc
                if parsed_length < 0:
                    await response.aclose()
                    raise UnsafeOutboundUrl("Longueur de réponse invalide")
                if parsed_length > max_bytes:
                    await response.aclose()
                    raise OutboundResponseTooLarge("Réponse distante trop volumineuse")
            body = bytearray()
            try:
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > max_bytes:
                        raise OutboundResponseTooLarge("Réponse distante trop volumineuse")
            finally:
                await response.aclose()
            return httpx.Response(
                response.status_code,
                headers=response.headers,
                content=bytes(body),
                request=response.request,
                extensions={"validated_url": current_url},
            )
        raise UnsafeOutboundUrl("Redirection refusée")

    @staticmethod
    def _origin(url: str) -> tuple[str, str, int]:
        parsed = urlsplit(url)
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        return parsed.scheme, parsed.hostname or "", port
