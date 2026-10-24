"""Worker persistant chargé d'acquérir les scans puis les tâches de crawl."""

import asyncio
import json
import os
import signal
import socket
from datetime import datetime
from threading import Event

import httpx

from app.connectors.configuration import enabled_registry
from app.connectors.registry import ConnectorRegistry
from app.connectors.runtime import build_runtime_registry
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.entities import ConnectorSecret, CrawlJob, DiscoveredURL, WebSource
from app.security.connector_secrets import ConnectorSecretVault
from app.security.outbound import (
    OutboundResponseTooLarge,
    OutboundResponseTypeRejected,
    SafeHttpClient,
    UnsafeOutboundUrl,
)
from app.services.crawl_processing import extract_page, persist_crawl_success
from app.services.crawl_queue import (
    claim_next_crawl_job,
    fail_crawl_job,
    schedule_crawl_retry,
)
from app.services.web_fetcher import (
    WebFetcher,
    WebFetchError,
    WebFetchResult,
    persistent_domain_gate,
)
from app.workers.queue import claim_next_scan, schedule_retry
from app.workers.rate_limit import defer_provider_until, wait_for_request_slot
from app.workers.runner import ScanRunner
from app.workers.scheduler import enqueue_due_schedules

stop_requested = Event()


def _request_stop(_signum: int, _frame: object) -> None:
    stop_requested.set()


def build_registry() -> ConnectorRegistry:
    settings = get_settings()
    with SessionLocal() as db:
        for connector_id, settings_field in (
            ("github", "github_api_token"),
            ("brave", "brave_api_token"),
        ):
            stored = db.get(ConnectorSecret, connector_id)
            if stored is None:
                continue
            token = ConnectorSecretVault(settings).decrypt(
                stored.connector_id, stored.ciphertext, stored.key_version
            )
            settings = settings.model_copy(update={settings_field: token})

    async def github_gate() -> None:
        await wait_for_request_slot("github", 10, should_stop=stop_requested.is_set)

    async def github_quota_exhausted(resume_at: datetime) -> None:
        with SessionLocal() as db:
            defer_provider_until(db, "github", resume_at)

    async def gitlab_gate() -> None:
        await wait_for_request_slot("gitlab", 10, should_stop=stop_requested.is_set)

    async def wayback_gate() -> None:
        await wait_for_request_slot("wayback", 5, should_stop=stop_requested.is_set)

    async def brave_gate() -> None:
        await wait_for_request_slot("brave", 5, should_stop=stop_requested.is_set)

    async def searxng_gate() -> None:
        await wait_for_request_slot("searxng", 5, should_stop=stop_requested.is_set)

    async def brave_quota_exhausted(resume_at: datetime) -> None:
        with SessionLocal() as db:
            defer_provider_until(db, "brave", resume_at)

    registry = build_runtime_registry(
        settings,
        github_request_gate=github_gate,
        github_quota_exhausted=github_quota_exhausted,
        gitlab_request_gate=gitlab_gate,
        wayback_request_gate=wayback_gate,
        brave_request_gate=brave_gate,
        brave_quota_exhausted=brave_quota_exhausted,
        searxng_request_gate=searxng_gate,
    )
    with SessionLocal() as db:
        return enabled_registry(db, registry)


def process_once(
    worker_id: str,
    registry: ConnectorRegistry | None = None,
    crawl_fetcher: WebFetcher | None = None,
) -> bool:
    with SessionLocal() as db:
        enqueue_due_schedules(db)
        scan_id = claim_next_scan(db, worker_id)
        if scan_id is not None:
            try:
                scan_registry = registry if registry is not None else build_registry()
                asyncio.run(ScanRunner(scan_registry).run(scan_id, db))
                print(json.dumps({"event": "scan.completed", "scan_id": scan_id}))
            except asyncio.CancelledError:
                db.rollback()
                schedule_retry(db, scan_id)
                print(json.dumps({"event": "scan.requeued_for_shutdown", "scan_id": scan_id}))
            except Exception:
                db.rollback()
                schedule_retry(db, scan_id)
                print(json.dumps({"event": "scan.retry_or_failed", "scan_id": scan_id}))
            return True
    return process_crawl_once(worker_id, crawl_fetcher)


async def _fetch_crawl_target(url: str, requests_per_minute: int) -> WebFetchResult:
    async with httpx.AsyncClient() as client:
        fetcher = WebFetcher(
            SafeHttpClient(client),
            domain_gate=persistent_domain_gate(
                requests_per_minute, should_stop=stop_requested.is_set
            ),
        )
        return await fetcher.fetch(url)


def process_crawl_once(worker_id: str, fetcher: WebFetcher | None = None) -> bool:
    with SessionLocal() as db:
        job_id = claim_next_crawl_job(db, worker_id)
        if job_id is None:
            return False
        try:
            job = db.get(CrawlJob, job_id)
            if job is None:
                raise RuntimeError("Tâche de crawl introuvable après acquisition")
            discovered = db.get(DiscoveredURL, job.discovered_url_id)
            if discovered is None:
                raise RuntimeError("URL de crawl introuvable après acquisition")
            source = db.get(WebSource, discovered.source_id) if discovered.source_id else None
            requests_per_minute = source.rate_limit_per_minute if source is not None else 5
            target_url = discovered.canonical_url
            # Ne pas conserver une transaction de lecture SQLite pendant que le
            # quota persistant réserve son créneau dans une autre session.
            db.rollback()
            if fetcher is None:
                fetched = asyncio.run(_fetch_crawl_target(target_url, requests_per_minute))
            else:
                fetched = asyncio.run(fetcher.fetch(target_url))
            extracted = extract_page(fetched)
            persist_crawl_success(
                db,
                job_id,
                fetched,
                extracted,
                worker_id=worker_id,
            )
            print(json.dumps({"event": "crawl.completed", "crawl_job_id": job_id}))
        except asyncio.CancelledError:
            db.rollback()
            schedule_crawl_retry(db, job_id, worker_id=worker_id, error_code="worker_shutdown")
            print(json.dumps({"event": "crawl.requeued_for_shutdown", "crawl_job_id": job_id}))
        except WebFetchError as exc:
            db.rollback()
            if exc.code in {"rate_limited", "remote_server_error", "robots_unavailable"}:
                schedule_crawl_retry(
                    db,
                    job_id,
                    worker_id=worker_id,
                    error_code=exc.code,
                    retry_after_seconds=exc.retry_after_seconds,
                )
                event = "crawl.retry_scheduled"
            else:
                fail_crawl_job(db, job_id, worker_id=worker_id, error_code=exc.code)
                event = "crawl.failed"
            print(json.dumps({"event": event, "crawl_job_id": job_id, "error_code": exc.code}))
        except httpx.TransportError:
            db.rollback()
            schedule_crawl_retry(db, job_id, worker_id=worker_id, error_code="network_error")
            print(
                json.dumps(
                    {
                        "event": "crawl.retry_scheduled",
                        "crawl_job_id": job_id,
                        "error_code": "network_error",
                    }
                )
            )
        except (OutboundResponseTooLarge, OutboundResponseTypeRejected, UnsafeOutboundUrl) as exc:
            db.rollback()
            error_code = {
                OutboundResponseTooLarge: "response_too_large",
                OutboundResponseTypeRejected: "mime_type_rejected",
                UnsafeOutboundUrl: "unsafe_destination",
            }[type(exc)]
            fail_crawl_job(db, job_id, worker_id=worker_id, error_code=error_code)
            print(
                json.dumps(
                    {"event": "crawl.failed", "crawl_job_id": job_id, "error_code": error_code}
                )
            )
        except Exception:
            db.rollback()
            schedule_crawl_retry(db, job_id, worker_id=worker_id, error_code="crawler_error")
            print(
                json.dumps(
                    {
                        "event": "crawl.retry_scheduled",
                        "crawl_job_id": job_id,
                        "error_code": "crawler_error",
                    }
                )
            )
        return True


def main() -> None:
    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)
    settings = get_settings()
    worker_id = f"{socket.gethostname()}-{os.getpid()}"
    while not stop_requested.is_set():
        if not process_once(worker_id):
            stop_requested.wait(settings.scan_worker_poll_seconds)


if __name__ == "__main__":
    main()
