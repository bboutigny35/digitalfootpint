import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.entities import CrawlStatistics, IdentityProfile, Scan, User
from app.services.crawl_queue import enqueue_discovered_url


def make_scan(db: Session) -> Scan:
    user = User(email="queue@example.test", password_hash="synthetic-test-hash")  # noqa: S106
    db.add(user)
    db.flush()
    profile = IdentityProfile(owner_id=user.id, first_name="Test", last_name="Queue")
    db.add(profile)
    db.flush()
    scan = Scan(owner_id=user.id, profile_id=profile.id, connector_ids=[])
    db.add(scan)
    db.commit()
    return scan


def test_enqueue_canonicalizes_deduplicates_and_counts(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path}/crawl.db")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        scan = make_scan(db)
        first = enqueue_discovered_url(
            db,
            scan,
            "HTTPS://Example.COM:443/path?utm_source=x&a=1#fragment",
            discovery_method="manual",
            priority=20,
        )
        duplicate = enqueue_discovered_url(
            db,
            scan,
            "https://example.com/path?a=1",
            discovery_method="sitemap",
        )
        assert first.created is True
        assert duplicate.created is False
        assert duplicate.crawl_job.id == first.crawl_job.id
        assert first.discovered_url.canonical_url == "https://example.com/path?a=1"
        statistics = db.get(CrawlStatistics, scan.id)
        assert statistics is not None
        assert (statistics.discovered_count, statistics.queued_count) == (1, 1)
    engine.dispose()


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://169.254.169.254/",
        "ftp://example.com/",
        "https://user:pass@example.com/",
        "https://example.com:8443/",
    ],
)
def test_enqueue_rejects_unsafe_syntax(tmp_path: Path, url: str) -> None:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path}/{uuid.uuid4()}.db")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        scan = make_scan(db)
        with pytest.raises(ValueError):
            enqueue_discovered_url(db, scan, url, discovery_method="manual")
    engine.dispose()
