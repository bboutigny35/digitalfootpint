import asyncio
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.connectors.base import (
    CandidateResult,
    Connector,
    ConnectorMetadata,
    IdentifierType,
    IdentitySnapshot,
)
from app.connectors.mock import MockConnector
from app.connectors.registry import ConnectorRegistry
from app.core.database import Base
from app.models.entities import (
    CrawlJob,
    CrawlResult,
    CrawlStatistics,
    DiscoveredURL,
    DiscoveryJob,
    IdentityProfile,
    Result,
    Scan,
    ScanStatus,
    User,
    WebSource,
)
from app.security.outbound import OutboundResponseTypeRejected
from app.security.passwords import hash_password
from app.services.crawl_queue import enqueue_discovered_url
from app.services.discovery_documents import DiscoveryBatch, DiscoveryCandidate
from app.services.discovery_fetcher import DiscoveryFetchError, DiscoveryFetchResult
from app.services.discovery_queue import enqueue_source_discovery
from app.services.web_fetcher import WebFetchError, WebFetchResult
from app.workers import scan_daemon


def _queued_scan(db: Session) -> Scan:
    user = User(email="daemon@example.test", password_hash=hash_password("synthetic-password"))
    db.add(user)
    db.flush()
    profile = IdentityProfile(
        owner_id=user.id,
        first_name="Test",
        last_name="Worker",
        pseudonyms=["test-worker"],
    )
    db.add(profile)
    db.flush()
    scan = Scan(owner_id=user.id, profile_id=profile.id, connector_ids=["mock"])
    db.add(scan)
    db.commit()
    return scan


def test_process_once_persists_results_and_completes_scan(tmp_path: Path, monkeypatch) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'worker.db'}")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        scan = _queued_scan(db)
        source = WebSource(
            domain="planned.example",
            base_url="https://planned.example/sitemap.xml",
            category="public",
            access_method="sitemap",
            state="active",
            priority=10,
        )
        db.add(source)
        db.commit()
    monkeypatch.setattr(scan_daemon, "SessionLocal", lambda: Session(engine))
    monkeypatch.setattr(
        scan_daemon,
        "build_registry",
        lambda: ConnectorRegistry([MockConnector()]),
    )

    assert scan_daemon.process_once("test-worker")

    with Session(engine) as db:
        completed = db.get(Scan, scan.id)
        result = db.scalar(select(Result).where(Result.scan_id == scan.id))
        discovery_job = db.scalar(select(DiscoveryJob).where(DiscoveryJob.scan_id == scan.id))
        crawl_job = db.scalar(select(CrawlJob).where(CrawlJob.scan_id == scan.id))
        assert completed is not None
        assert completed.status == ScanStatus.COMPLETED
        assert result is not None
        assert result.connector_id == "mock"
        assert discovery_job is not None
        assert discovery_job.source_id == source.id
        assert discovery_job.status == "queued"
        assert crawl_job is None
    engine.dispose()


class _FailingConnector(Connector):
    metadata = ConnectorMetadata(
        identifier="mock",
        version="test",
        capabilities=("test",),
        accepted_identifiers=(IdentifierType.PSEUDONYM,),
    )

    async def search(self, identity: IdentitySnapshot) -> list[CandidateResult]:
        del identity
        raise RuntimeError("synthetic provider failure")


class _CrawlableConnector(Connector):
    metadata = ConnectorMetadata(
        identifier="crawlable",
        version="test",
        capabilities=("public_profiles",),
        accepted_identifiers=(IdentifierType.PSEUDONYM,),
        crawl_results=True,
    )

    async def search(self, identity: IdentitySnapshot) -> list[CandidateResult]:
        del identity
        return [
            CandidateResult(
                url="https://public.example/profile",
                title="Public profile",
                snippet="Synthetic public result",
                match_type="pseudonym",
            ),
            CandidateResult(
                url="http://127.0.0.1/private",
                title="Rejected crawl target",
                snippet="Synthetic local result",
                match_type="pseudonym",
            ),
        ]


def test_process_once_requeues_failure_with_generic_error(tmp_path: Path, monkeypatch) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'worker-failure.db'}")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        scan = _queued_scan(db)
    monkeypatch.setattr(scan_daemon, "SessionLocal", lambda: Session(engine))

    assert scan_daemon.process_once("test-worker", ConnectorRegistry([_FailingConnector()]))

    with Session(engine) as db:
        retried = db.get(Scan, scan.id)
        assert retried is not None
        assert retried.status == ScanStatus.QUEUED
        assert retried.error_code == "retry_scheduled"
    engine.dispose()


def test_authorized_connector_results_feed_crawl_without_failing_on_rejected_url(
    tmp_path: Path, monkeypatch
) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'connector-crawl.db'}")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        scan = _queued_scan(db)
        scan.connector_ids = ["crawlable"]
        db.commit()
    monkeypatch.setattr(scan_daemon, "SessionLocal", lambda: Session(engine))

    assert scan_daemon.process_once("test-worker", ConnectorRegistry([_CrawlableConnector()]))

    with Session(engine) as db:
        completed = db.get(Scan, scan.id)
        results = list(db.scalars(select(Result).where(Result.scan_id == scan.id)))
        discovered = list(db.scalars(select(DiscoveredURL).where(DiscoveredURL.scan_id == scan.id)))
        crawl_jobs = list(db.scalars(select(CrawlJob).where(CrawlJob.scan_id == scan.id)))
        assert completed is not None and completed.status == ScanStatus.COMPLETED
        assert len(results) == 2
        assert len(discovered) == 1
        assert discovered[0].canonical_url == "https://public.example/profile"
        assert discovered[0].discovery_method == "connector:crawlable"
        assert len(crawl_jobs) == 1
    engine.dispose()


def test_process_once_requeues_scan_on_graceful_shutdown(tmp_path: Path, monkeypatch) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'worker-shutdown.db'}")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        scan = _queued_scan(db)
    monkeypatch.setattr(scan_daemon, "SessionLocal", lambda: Session(engine))

    async def cancel_run(self: object, scan_id: str, db: Session) -> None:
        del self, scan_id, db
        raise asyncio.CancelledError("worker shutdown")

    monkeypatch.setattr(scan_daemon.ScanRunner, "run", cancel_run)
    assert scan_daemon.process_once("test-worker", ConnectorRegistry([MockConnector()]))

    with Session(engine) as db:
        retried = db.get(Scan, scan.id)
        assert retried is not None
        assert retried.status == ScanStatus.QUEUED
        assert retried.error_code == "retry_scheduled"
    engine.dispose()


class _SuccessfulFetcher:
    async def fetch(self, url: str) -> WebFetchResult:
        return WebFetchResult(
            final_url=url,
            http_status=200,
            mime_type="text/html",
            content=b"<html><body>Public profile</body></html>",
        )


class _RetryingFetcher:
    async def fetch(self, _url: str) -> WebFetchResult:
        raise WebFetchError("rate_limited", retry_after_seconds=60)


class _RejectedFetcher:
    async def fetch(self, _url: str) -> WebFetchResult:
        raise OutboundResponseTypeRejected("synthetic rejection")


class _CancelledFetcher:
    async def fetch(self, _url: str) -> WebFetchResult:
        raise asyncio.CancelledError("synthetic shutdown")


def _completed_scan_with_crawl(db: Session) -> tuple[Scan, str]:
    scan = _queued_scan(db)
    scan.status = ScanStatus.COMPLETED
    db.commit()
    queued = enqueue_discovered_url(
        db, scan, "https://example.test/profile", discovery_method="manual"
    )
    return scan, queued.crawl_job.id


def _completed_scan_with_discovery(db: Session) -> tuple[Scan, str]:
    scan = _queued_scan(db)
    scan.status = ScanStatus.COMPLETED
    source = WebSource(
        domain="example.test",
        base_url="https://example.test/sitemap.xml",
        category="public",
        access_method="sitemap",
        state="active",
        priority=10,
    )
    db.add(source)
    db.commit()
    queued = enqueue_source_discovery(db, scan, source)
    return scan, queued.job.id


class _SuccessfulDiscoveryFetcher:
    async def fetch(self, _source: WebSource) -> DiscoveryFetchResult:
        return DiscoveryFetchResult(
            batch=DiscoveryBatch(
                items=(
                    DiscoveryCandidate(
                        url="https://example.test/profile",
                        kind="page",
                    ),
                )
            ),
            fetched_document_count=1,
        )


class _RetryingDiscoveryFetcher:
    async def fetch(self, _source: WebSource) -> DiscoveryFetchResult:
        raise DiscoveryFetchError("rate_limited", retry_after_seconds=60)


class _RejectedDiscoveryFetcher:
    async def fetch(self, _source: WebSource) -> DiscoveryFetchResult:
        raise DiscoveryFetchError("source_redirect_outside_domain")


def test_process_once_runs_crawl_after_scan_queue(tmp_path: Path, monkeypatch, capsys) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'crawl-worker.db'}")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        scan, job_id = _completed_scan_with_crawl(db)
    monkeypatch.setattr(scan_daemon, "SessionLocal", lambda: Session(engine))

    assert scan_daemon.process_once("crawl-worker", crawl_fetcher=_SuccessfulFetcher())  # type: ignore[arg-type]

    with Session(engine) as db:
        job = db.get(CrawlJob, job_id)
        result = db.scalar(select(CrawlResult).where(CrawlResult.crawl_job_id == job_id))
        statistics = db.get(CrawlStatistics, scan.id)
        assert job is not None and job.status == "completed"
        assert result is not None and result.extracted_text == "Public profile"
        assert statistics is not None and statistics.fetched_count == 1
    output = capsys.readouterr().out
    assert "crawl.completed" in output
    assert "example.test" not in output
    engine.dispose()


def test_process_once_runs_discovery_before_crawl(tmp_path: Path, monkeypatch, capsys) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'discovery-worker.db'}")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        scan, job_id = _completed_scan_with_discovery(db)
    monkeypatch.setattr(scan_daemon, "SessionLocal", lambda: Session(engine))

    assert scan_daemon.process_once(
        "discovery-worker",
        discovery_fetcher=_SuccessfulDiscoveryFetcher(),  # type: ignore[arg-type]
    )

    with Session(engine) as db:
        job = db.get(DiscoveryJob, job_id)
        discovered = db.scalar(select(DiscoveredURL).where(DiscoveredURL.scan_id == scan.id))
        crawl_job = db.scalar(select(CrawlJob).where(CrawlJob.scan_id == scan.id))
        assert job is not None and job.status == "completed"
        assert discovered is not None and discovered.discovery_method == "sitemap"
        assert crawl_job is not None and crawl_job.status == "queued"
    output = capsys.readouterr().out
    assert "discovery.completed" in output
    assert "example.test" not in output
    engine.dispose()


def test_discovery_worker_distinguishes_retryable_and_terminal_errors(
    tmp_path: Path, monkeypatch
) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'discovery-errors.db'}")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        _scan, job_id = _completed_scan_with_discovery(db)
    monkeypatch.setattr(scan_daemon, "SessionLocal", lambda: Session(engine))

    assert scan_daemon.process_discovery_once(
        "discovery-worker",
        _RetryingDiscoveryFetcher(),  # type: ignore[arg-type]
    )
    with Session(engine) as db:
        job = db.get(DiscoveryJob, job_id)
        assert job is not None
        assert job.status == "queued"
        assert job.error_code == "retry_scheduled"
        job.next_attempt_at = None
        db.commit()

    assert scan_daemon.process_discovery_once(
        "discovery-worker",
        _RejectedDiscoveryFetcher(),  # type: ignore[arg-type]
    )
    with Session(engine) as db:
        job = db.get(DiscoveryJob, job_id)
        assert job is not None
        assert job.status == "failed"
        assert job.error_code == "source_redirect_outside_domain"
    engine.dispose()


def test_crawl_worker_distinguishes_retryable_and_terminal_errors(
    tmp_path: Path, monkeypatch
) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'crawl-errors.db'}")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        _scan, retry_job_id = _completed_scan_with_crawl(db)
    monkeypatch.setattr(scan_daemon, "SessionLocal", lambda: Session(engine))

    assert scan_daemon.process_crawl_once("crawl-worker", _RetryingFetcher())  # type: ignore[arg-type]
    with Session(engine) as db:
        retry_job = db.get(CrawlJob, retry_job_id)
        assert retry_job is not None
        assert retry_job.status == "queued"
        assert retry_job.error_code == "retry_scheduled"
        retry_job.next_attempt_at = None
        db.commit()

    assert scan_daemon.process_crawl_once("crawl-worker", _RejectedFetcher())  # type: ignore[arg-type]
    with Session(engine) as db:
        failed_job = db.get(CrawlJob, retry_job_id)
        statistics = db.get(CrawlStatistics, failed_job.scan_id) if failed_job else None
        assert failed_job is not None
        assert failed_job.status == "failed"
        assert failed_job.error_code == "mime_type_rejected"
        assert statistics is not None and statistics.failed_count == 1
    engine.dispose()


def test_crawl_worker_requeues_on_graceful_shutdown(tmp_path: Path, monkeypatch) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'crawl-shutdown.db'}")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as db:
        _scan, job_id = _completed_scan_with_crawl(db)
    monkeypatch.setattr(scan_daemon, "SessionLocal", lambda: Session(engine))

    assert scan_daemon.process_crawl_once("crawl-worker", _CancelledFetcher())  # type: ignore[arg-type]
    with Session(engine) as db:
        job = db.get(CrawlJob, job_id)
        assert job is not None
        assert job.status == "queued"
        assert job.error_code == "retry_scheduled"
        assert job.lease_owner is None
    engine.dispose()
