import json
import signal
from dataclasses import asdict
from threading import Event

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.workers.retention import purge_expired_descriptors

stop_requested = Event()


def _request_stop(_signum: int, _frame: object) -> None:
    stop_requested.set()


def run_once() -> int:
    deleted = 0
    while True:
        with SessionLocal() as db:
            result = purge_expired_descriptors(db)
        deleted += result.deleted_descriptors
        if result.deleted_descriptors < 500:
            print(json.dumps(asdict(result) | {"event": "retention.completed", "total": deleted}))
            return deleted


def main() -> None:
    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)
    interval = get_settings().sensitive_retention_interval_seconds
    while not stop_requested.is_set():
        try:
            run_once()
        except Exception:
            print(json.dumps({"event": "retention.failed", "error_code": "maintenance_failure"}))
        stop_requested.wait(interval)


if __name__ == "__main__":
    main()
