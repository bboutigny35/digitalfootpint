import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.entities import (
    CrawlJob,
    CrawlResult,
    CrawlStatistics,
    DiscoveredURL,
    Evidence,
    EvidenceMatch,
    IdentityCorrelation,
    IdentityProfile,
    Result,
    Scan,
    User,
    WebSource,
)
from app.services.crawl_processing import extract_page, persist_crawl_success
from app.services.crawl_queue import claim_next_crawl_job, enqueue_discovered_url
from app.services.web_fetcher import WebFetchResult


def make_scan(db: Session) -> Scan:
    user = User(email="processing@example.test", password_hash="synthetic-test-hash")  # noqa: S106
    db.add(user)
    db.flush()
    profile = IdentityProfile(
        owner_id=user.id,
        first_name="Test",
        last_name="Processing",
        pseudonyms=["ProcessFox"],
        employers=["Example Org"],
    )
    db.add(profile)
    db.flush()
    scan = Scan(owner_id=user.id, profile_id=profile.id, connector_ids=[])
    db.add(scan)
    db.commit()
    return scan


def test_extract_page_minimizes_text_and_keeps_only_same_host_links() -> None:
    body = b"""
        <html><head><style>secret style</style><script>secret script</script></head>
        <body><h1> Public   profile </h1>
        <a href="/next#section">Next</a>
        <a href="https://other.example/path">Other host</a>
        <a href="javascript:alert(1)">Script link</a>
        </body></html>
    """
    extracted = extract_page(
        WebFetchResult(
            final_url="https://example.test/start",
            http_status=200,
            mime_type="text/html",
            content=body,
        )
    )
    assert extracted.text == "Public profile Next Other host Script link"
    assert "secret" not in extracted.text
    assert extracted.links == ("https://example.test/next#section",)


def test_persist_success_is_atomic_minimized_and_idempotent(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path}/processing.db")
    Base.metadata.create_all(engine)
    now = datetime(2026, 1, 1, tzinfo=UTC)
    body = (
        b'<html><body>Test Processing, also ProcessFox at Example Org. '
        b'<a href="/next">next</a></body></html>'
    )
    fetch = WebFetchResult(
        final_url="https://example.test/root",
        http_status=200,
        mime_type="text/html",
        content=body,
    )
    with Session(engine) as db:
        scan = make_scan(db)
        source = WebSource(
            domain="example.test",
            base_url="https://example.test/",
            category="web",
            access_method="crawl",
            cache_ttl_seconds=3600,
        )
        db.add(source)
        connector_result = Result(
            owner_id=scan.owner_id,
            profile_id=scan.profile_id,
            scan_id=scan.id,
            connector_id="synthetic",
            canonical_url=fetch.final_url,
            domain="example.test",
            title="Synthetic public profile",
            snippet="Synthetic snippet",
            match_type="profile",
            relevance_score=0.45,
            score_explanation={"method": "test"},
        )
        db.add(connector_result)
        db.commit()
        queued = enqueue_discovered_url(
            db,
            scan,
            fetch.final_url,
            source_id=source.id,
            discovery_method="connector:synthetic",
            priority=20,
        )
        assert claim_next_crawl_job(db, "worker", now) == queued.crawl_job.id
        extracted = extract_page(fetch)
        with pytest.raises(ValueError, match="n'est pas acquise"):
            persist_crawl_success(
                db, queued.crawl_job.id, fetch, extracted, worker_id="stale-worker", now=now
            )
        result = persist_crawl_success(
            db, queued.crawl_job.id, fetch, extracted, worker_id="worker", now=now
        )

        assert result.extracted_text == (
            "Test Processing, also ProcessFox at Example Org. next"
        )
        assert result.content_length == len(body)
        assert result.content_hash == hashlib.sha256(body).hexdigest()
        assert result.cache_expires_at is not None
        assert result.cache_expires_at.replace(tzinfo=UTC) == now + timedelta(hours=1)
        assert not hasattr(result, "raw_content")
        job = db.get(CrawlJob, queued.crawl_job.id)
        assert job is not None
        assert job.status == "completed"
        assert job.lease_owner is None
        discovered = list(db.scalars(select(DiscoveredURL).where(DiscoveredURL.scan_id == scan.id)))
        assert [item.canonical_url for item in discovered] == [
            "https://example.test/root",
            "https://example.test/next",
        ]
        statistics = db.get(CrawlStatistics, scan.id)
        assert statistics is not None
        assert (statistics.discovered_count, statistics.queued_count) == (2, 1)
        assert (statistics.fetched_count, statistics.bytes_downloaded) == (1, len(body))
        db.refresh(source)
        assert source.discovered_url_count == 2
        assert source.crawled_page_count == 1
        assert source.last_checked_at is not None

        correlation = db.scalar(
            select(IdentityCorrelation).where(
                IdentityCorrelation.result_id == connector_result.id
            )
        )
        assert correlation is not None
        assert correlation.relevance_score == 0.45
        assert correlation.attribution_score == 0.55
        assert correlation.evidence_count == 1
        evidence = db.scalar(
            select(Evidence).where(Evidence.crawl_result_id == result.id)
        )
        assert evidence is not None
        assert evidence.result_id == connector_result.id
        assert len(evidence.excerpt) <= 500
        assert evidence.provenance == {
            "method": "exact-identity-evidence-v1",
            "discovery_method": "connector:synthetic",
            "match_count": 3,
        }
        matches = list(
            db.scalars(select(EvidenceMatch).where(EvidenceMatch.evidence_id == evidence.id))
        )
        assert {item.criterion_type for item in matches} == {
            "name",
            "pseudonym",
            "employer",
        }
        assert all("Test Processing" not in item.criterion_hash for item in matches)

        same_result = persist_crawl_success(
            db, queued.crawl_job.id, fetch, extracted, worker_id="worker", now=now
        )
        assert same_result.id == result.id
        assert db.scalar(select(CrawlResult).where(CrawlResult.crawl_job_id == job.id)) is not None
        db.refresh(statistics)
        assert statistics.fetched_count == 1
        assert db.scalar(
            select(IdentityCorrelation).where(
                IdentityCorrelation.result_id == connector_result.id
            )
        ) is not None

        secondary_job_id = claim_next_crawl_job(db, "worker", now)
        assert secondary_job_id is not None
        secondary_fetch = WebFetchResult(
            final_url="https://example.test/next",
            http_status=200,
            mime_type="text/plain",
            content=b"Test Processing at a secondary page",
        )
        secondary = persist_crawl_success(
            db,
            secondary_job_id,
            secondary_fetch,
            extract_page(secondary_fetch),
            worker_id="worker",
            now=now,
        )
        assert db.scalar(
            select(Evidence).where(Evidence.crawl_result_id == secondary.id)
        ) is None
        assert len(list(db.scalars(select(IdentityCorrelation)))) == 1
    engine.dispose()


def test_plain_text_does_not_discover_embedded_urls() -> None:
    extracted = extract_page(
        WebFetchResult(
            final_url="https://example.test/plain",
            http_status=200,
            mime_type="text/plain",
            content=b"Public text https://example.test/not-a-link",
        )
    )
    assert extracted.text == "Public text https://example.test/not-a-link"
    assert extracted.links == ()
