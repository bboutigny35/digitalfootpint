"""Worker persistant chargé d'acquérir et d'exécuter les scans."""

import asyncio
import json
import os
import signal
import socket
from datetime import datetime
from threading import Event

from app.connectors.configuration import enabled_registry
from app.connectors.registry import ConnectorRegistry
from app.connectors.runtime import build_runtime_registry
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.entities import ConnectorSecret
from app.security.connector_secrets import ConnectorSecretVault
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


def process_once(worker_id: str, registry: ConnectorRegistry | None = None) -> bool:
    with SessionLocal() as db:
        enqueue_due_schedules(db)
        scan_id = claim_next_scan(db, worker_id)
        if scan_id is None:
            return False
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
