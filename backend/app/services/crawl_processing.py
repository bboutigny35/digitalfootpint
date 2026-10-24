"""Extraction minimisée et persistance atomique des téléchargements de crawl."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import (
    CrawlJob,
    CrawlResult,
    CrawlStatistics,
    DiscoveredURL,
    Scan,
    WebSource,
)
from app.services.correlation import analyze_crawl_evidence
from app.services.crawl_queue import MAX_DEPTH, enqueue_discovered_url
from app.services.web_fetcher import WebFetchResult

MAX_EXTRACTED_TEXT_CHARS = 100_000
MAX_LINKS_PER_PAGE = 50
DEFAULT_CACHE_TTL = timedelta(hours=24)
_WHITESPACE = re.compile(r"\s+")
_IGNORED_ELEMENTS = {"script", "style", "noscript", "template", "svg"}


@dataclass(frozen=True, slots=True)
class ExtractedPage:
    text: str
    links: tuple[str, ...]


class _MinimalHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_parts: list[str] = []
        self.links: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.casefold()
        if normalized_tag in _IGNORED_ELEMENTS:
            self._ignored_depth += 1
            return
        if normalized_tag != "a" or self._ignored_depth:
            return
        href = next((value for name, value in attrs if name.casefold() == "href"), None)
        if href:
            self.links.append(href)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() == "a" and not self._ignored_depth:
            href = next((value for name, value in attrs if name.casefold() == "href"), None)
            if href:
                self.links.append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() in _IGNORED_ELEMENTS and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self.text_parts.append(data)


def extract_page(fetch: WebFetchResult) -> ExtractedPage:
    decoded = fetch.content.decode("utf-8", errors="replace")
    if fetch.mime_type == "text/plain":
        text = _normalize_text(decoded)
        return ExtractedPage(text=text, links=())
    parser = _MinimalHTMLParser()
    parser.feed(decoded)
    parser.close()
    text = _normalize_text(" ".join(parser.text_parts))
    links = _admissible_links(fetch.final_url, parser.links)
    return ExtractedPage(text=text, links=links)


def _normalize_text(value: str) -> str:
    return _WHITESPACE.sub(" ", value).strip()[:MAX_EXTRACTED_TEXT_CHARS]


def _admissible_links(base_url: str, raw_links: list[str]) -> tuple[str, ...]:
    base_hostname = (urlsplit(base_url).hostname or "").casefold().rstrip(".")
    admitted: list[str] = []
    seen: set[str] = set()
    for raw_link in raw_links:
        candidate = urljoin(base_url, raw_link.strip())
        parsed = urlsplit(candidate)
        hostname = (parsed.hostname or "").casefold().rstrip(".")
        if parsed.scheme not in {"http", "https"} or hostname != base_hostname:
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        admitted.append(candidate)
        if len(admitted) >= MAX_LINKS_PER_PAGE:
            break
    return tuple(admitted)


def persist_crawl_success(
    db: Session,
    job_id: str,
    fetch: WebFetchResult,
    extracted: ExtractedPage,
    *,
    worker_id: str,
    now: datetime | None = None,
) -> CrawlResult:
    fetched_at = now or datetime.now(UTC)
    job = db.get(CrawlJob, job_id)
    if job is None:
        raise ValueError("Tâche de crawl introuvable")
    existing = db.scalar(select(CrawlResult).where(CrawlResult.crawl_job_id == job.id))
    if existing is not None:
        return existing
    if job.status != "running" or job.lease_owner != worker_id:
        raise ValueError("La tâche de crawl n'est pas acquise")
    if job.lease_expires_at is None or _timestamp(job.lease_expires_at) <= _timestamp(fetched_at):
        raise ValueError("Le bail de crawl a expiré")
    discovered = db.get(DiscoveredURL, job.discovered_url_id)
    scan = db.get(Scan, job.scan_id)
    statistics = db.get(CrawlStatistics, job.scan_id)
    if discovered is None or scan is None or statistics is None:
        raise RuntimeError("État de crawl incomplet")
    source = db.get(WebSource, discovered.source_id) if discovered.source_id is not None else None
    cache_ttl = (
        timedelta(seconds=source.cache_ttl_seconds) if source is not None else DEFAULT_CACHE_TTL
    )

    result = CrawlResult(
        crawl_job_id=job.id,
        http_status=fetch.http_status,
        final_url=fetch.final_url,
        mime_type=fetch.mime_type,
        content_length=len(fetch.content),
        content_hash=hashlib.sha256(fetch.content).hexdigest(),
        extracted_text=extracted.text or None,
        fetched_at=fetched_at,
        cache_expires_at=fetched_at + cache_ttl,
    )
    db.add(result)
    db.flush()
    analyze_crawl_evidence(
        db,
        scan=scan,
        discovered=discovered,
        crawl_result=result,
    )
    if discovered.depth < MAX_DEPTH:
        for link in extracted.links:
            try:
                enqueue_discovered_url(
                    db,
                    scan,
                    link,
                    source_id=discovered.source_id,
                    discovery_method="page_link",
                    depth=discovered.depth + 1,
                    priority=min(job.priority + 10, 1000),
                    commit=False,
                )
            except ValueError:
                continue
    job.status = "completed"
    job.finished_at = fetched_at
    job.lease_owner = None
    job.lease_expires_at = None
    job.error_code = None
    statistics.fetched_count += 1
    statistics.queued_count = max(statistics.queued_count - 1, 0)
    statistics.bytes_downloaded += len(fetch.content)
    if source is not None:
        source.crawled_page_count += 1
        source.last_checked_at = fetched_at
        source.last_error_code = None
    db.commit()
    db.refresh(result)
    return result


def _timestamp(value: datetime) -> float:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.timestamp()
