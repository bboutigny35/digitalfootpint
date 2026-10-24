"""Normalisation hermétique des documents sitemap, RSS et Atom."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, cast
from urllib.parse import urlsplit
from xml.etree.ElementTree import Element as XmlElement

from defusedxml import ElementTree  # type: ignore[import-untyped]
from defusedxml.common import DefusedXmlException  # type: ignore[import-untyped]
from sqlalchemy.orm import Session

from app.models.entities import Scan, WebSource
from app.services.crawl_queue import enqueue_discovered_url

MAX_DISCOVERY_DOCUMENT_BYTES = 512 * 1024
MAX_DISCOVERY_ITEMS = 1000
MAX_NESTED_SITEMAPS = 50


class DiscoveryDocumentError(ValueError):
    """Document refusé sans reproduire son contenu dans l'erreur."""


@dataclass(frozen=True, slots=True)
class DiscoveryCandidate:
    url: str
    kind: Literal["page", "sitemap"]
    title: str | None = None
    published_at: str | None = None


@dataclass(frozen=True, slots=True)
class DiscoveryBatch:
    items: tuple[DiscoveryCandidate, ...]
    nested_sitemaps: tuple[DiscoveryCandidate, ...] = ()


@dataclass(frozen=True, slots=True)
class DiscoveryEnqueueResult:
    parsed_count: int
    created_count: int
    nested_sitemaps: tuple[str, ...]


def parse_discovery_document(
    content: bytes,
    *,
    access_method: str,
    source_domain: str,
) -> DiscoveryBatch:
    if len(content) > MAX_DISCOVERY_DOCUMENT_BYTES:
        raise DiscoveryDocumentError("Document de découverte trop volumineux")
    upper_prefix = content[:4096].upper()
    if b"<!DOCTYPE" in upper_prefix or b"<!ENTITY" in upper_prefix:
        raise DiscoveryDocumentError("Déclarations XML interdites")
    try:
        root = cast(XmlElement, ElementTree.fromstring(content))
    except (ElementTree.ParseError, DefusedXmlException) as exc:
        raise DiscoveryDocumentError("Document XML invalide") from exc
    if access_method == "sitemap":
        return _parse_sitemap(root, source_domain)
    if access_method == "feed":
        return _parse_feed(root, source_domain)
    raise DiscoveryDocumentError("Méthode de découverte non prise en charge")


def enqueue_discovery_document(
    db: Session,
    scan: Scan,
    source: WebSource,
    content: bytes,
    *,
    now: datetime | None = None,
) -> DiscoveryEnqueueResult:
    if source.state != "active":
        raise DiscoveryDocumentError("Source Web inactive")
    batch = parse_discovery_document(
        content,
        access_method=source.access_method,
        source_domain=source.domain,
    )
    return enqueue_discovery_batch(db, scan, source, batch, now=now)


def enqueue_discovery_batch(
    db: Session,
    scan: Scan,
    source: WebSource,
    batch: DiscoveryBatch,
    *,
    now: datetime | None = None,
) -> DiscoveryEnqueueResult:
    if source.state != "active":
        raise DiscoveryDocumentError("Source Web inactive")
    created_count = 0
    for candidate in batch.items:
        try:
            enqueued = enqueue_discovered_url(
                db,
                scan,
                candidate.url,
                source_id=source.id,
                discovery_method=source.access_method,
                priority=source.priority,
                commit=False,
            )
        except ValueError:
            continue
        created_count += int(enqueued.created)
    source.last_checked_at = now or datetime.now(UTC)
    source.last_error_code = None
    db.commit()
    return DiscoveryEnqueueResult(
        parsed_count=len(batch.items),
        created_count=created_count,
        nested_sitemaps=tuple(item.url for item in batch.nested_sitemaps),
    )


def _parse_sitemap(root: XmlElement, source_domain: str) -> DiscoveryBatch:
    root_name = _local_name(root.tag)
    if root_name == "urlset":
        items = _unique_candidates(
            DiscoveryCandidate(url=location, kind="page", published_at=last_modified)
            for node in root
            if _local_name(node.tag) == "url"
            for location, last_modified in [
                (_child_text(node, "loc"), _bounded_text(_child_text(node, "lastmod"), 100))
            ]
            if location and _allowed_url(location, source_domain)
        )
        return DiscoveryBatch(items=items[:MAX_DISCOVERY_ITEMS])
    if root_name == "sitemapindex":
        nested = _unique_candidates(
            DiscoveryCandidate(url=location, kind="sitemap", published_at=last_modified)
            for node in root
            if _local_name(node.tag) == "sitemap"
            for location, last_modified in [
                (_child_text(node, "loc"), _bounded_text(_child_text(node, "lastmod"), 100))
            ]
            if location and _allowed_url(location, source_domain)
        )
        return DiscoveryBatch(items=(), nested_sitemaps=nested[:MAX_NESTED_SITEMAPS])
    raise DiscoveryDocumentError("Format sitemap non reconnu")


def _parse_feed(root: XmlElement, source_domain: str) -> DiscoveryBatch:
    root_name = _local_name(root.tag)
    if root_name == "rss":
        channel = next((node for node in root if _local_name(node.tag) == "channel"), None)
        entries = (
            [] if channel is None else [node for node in channel if _local_name(node.tag) == "item"]
        )
        candidates = (
            DiscoveryCandidate(
                url=link,
                kind="page",
                title=_bounded_text(_child_text(entry, "title"), 300),
                published_at=_bounded_text(_child_text(entry, "pubDate"), 100),
            )
            for entry in entries
            for link in [_child_text(entry, "link")]
            if link and _allowed_url(link, source_domain)
        )
    elif root_name == "feed":
        entries = [node for node in root if _local_name(node.tag) == "entry"]
        candidates = (
            DiscoveryCandidate(
                url=link,
                kind="page",
                title=_bounded_text(_child_text(entry, "title"), 300),
                published_at=_bounded_text(
                    _child_text(entry, "published") or _child_text(entry, "updated"), 100
                ),
            )
            for entry in entries
            for link in [_atom_link(entry)]
            if link and _allowed_url(link, source_domain)
        )
    else:
        raise DiscoveryDocumentError("Format de flux non reconnu")
    return DiscoveryBatch(items=_unique_candidates(candidates)[:MAX_DISCOVERY_ITEMS])


def _unique_candidates(
    candidates: Iterable[DiscoveryCandidate],
) -> tuple[DiscoveryCandidate, ...]:
    unique: list[DiscoveryCandidate] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate.url in seen:
            continue
        seen.add(candidate.url)
        unique.append(candidate)
    return tuple(unique)


def _allowed_url(url: str, source_domain: str) -> bool:
    try:
        parsed = urlsplit(url.strip())
        hostname = (parsed.hostname or "").casefold().rstrip(".")
        return (
            parsed.scheme in {"http", "https"}
            and parsed.username is None
            and parsed.password is None
            and parsed.port in {None, 80, 443}
            and hostname == source_domain.casefold().rstrip(".")
        )
    except ValueError:
        return False


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].casefold()


def _child_text(node: XmlElement, name: str) -> str | None:
    child = next((item for item in node if _local_name(item.tag) == name), None)
    return child.text.strip() if child is not None and child.text else None


def _atom_link(entry: XmlElement) -> str | None:
    for child in entry:
        if _local_name(child.tag) != "link":
            continue
        if child.attrib.get("rel", "alternate") in {"", "alternate"}:
            href = child.attrib.get("href")
            if href:
                return href.strip()
    return None


def _bounded_text(value: str | None, limit: int) -> str | None:
    return value[:limit] if value else None
