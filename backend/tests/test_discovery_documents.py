from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.entities import DiscoveredURL, IdentityProfile, Scan, User, WebSource
from app.services.discovery_documents import (
    DiscoveryDocumentError,
    enqueue_discovery_document,
    parse_discovery_document,
)


def test_sitemap_normalizes_same_domain_urls_and_nested_documents() -> None:
    sitemap = b"""<?xml version="1.0"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://example.test/profile</loc><lastmod>2026-01-02</lastmod></url>
      <url><loc>https://other.test/foreign</loc></url>
      <url><loc>https://example.test/profile</loc></url>
    </urlset>"""
    batch = parse_discovery_document(sitemap, access_method="sitemap", source_domain="example.test")
    assert [(item.url, item.kind) for item in batch.items] == [
        ("https://example.test/profile", "page")
    ]
    assert batch.items[0].published_at == "2026-01-02"

    index = b"""<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <sitemap><loc>https://example.test/sitemap-pages.xml</loc></sitemap>
      <sitemap><loc>https://other.test/sitemap.xml</loc></sitemap>
    </sitemapindex>"""
    nested = parse_discovery_document(index, access_method="sitemap", source_domain="example.test")
    assert nested.items == ()
    assert [item.url for item in nested.nested_sitemaps] == [
        "https://example.test/sitemap-pages.xml"
    ]


def test_rss_and_atom_share_normalized_candidate_contract() -> None:
    rss = b"""<rss version="2.0"><channel><item>
      <title>Public profile</title><link>https://example.test/rss-profile</link>
      <pubDate>Wed, 01 Jan 2026 10:00:00 GMT</pubDate>
    </item></channel></rss>"""
    atom = b"""<feed xmlns="http://www.w3.org/2005/Atom"><entry>
      <title>Atom profile</title><link rel="alternate" href="https://example.test/atom-profile" />
      <updated>2026-01-01T10:00:00Z</updated>
    </entry></feed>"""
    rss_batch = parse_discovery_document(rss, access_method="feed", source_domain="example.test")
    atom_batch = parse_discovery_document(atom, access_method="feed", source_domain="example.test")
    assert rss_batch.items[0].title == "Public profile"
    assert rss_batch.items[0].kind == "page"
    assert atom_batch.items[0].url == "https://example.test/atom-profile"
    assert atom_batch.items[0].published_at == "2026-01-01T10:00:00Z"


def test_discovery_parser_rejects_dtd_and_unsupported_documents() -> None:
    with pytest.raises(DiscoveryDocumentError, match="interdites"):
        parse_discovery_document(
            b'<!DOCTYPE x [<!ENTITY y "unsafe">]><urlset/>',
            access_method="sitemap",
            source_domain="example.test",
        )
    with pytest.raises(DiscoveryDocumentError, match="non reconnu"):
        parse_discovery_document(b"<html/>", access_method="feed", source_domain="example.test")


def test_active_source_enqueues_document_atomically_with_provenance(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path}/discovery.db")
    Base.metadata.create_all(engine)
    checked_at = datetime(2026, 1, 1, tzinfo=UTC)
    with Session(engine) as db:
        user = User(email="discovery@example.test", password_hash="synthetic-test-hash")  # noqa: S106
        db.add(user)
        db.flush()
        profile = IdentityProfile(owner_id=user.id, first_name="Test", last_name="Discovery")
        db.add(profile)
        db.flush()
        scan = Scan(owner_id=user.id, profile_id=profile.id, connector_ids=[])
        source = WebSource(
            domain="example.test",
            base_url="https://example.test/sitemap.xml",
            category="portfolio",
            access_method="sitemap",
            state="active",
            priority=30,
        )
        db.add_all([scan, source])
        db.commit()
        result = enqueue_discovery_document(
            db,
            scan,
            source,
            b"""<urlset><url><loc>https://example.test/a</loc></url>
            <url><loc>https://example.test/b</loc></url></urlset>""",
            now=checked_at,
        )
        assert (result.parsed_count, result.created_count) == (2, 2)
        discovered = list(db.scalars(select(DiscoveredURL).order_by(DiscoveredURL.canonical_url)))
        assert [item.canonical_url for item in discovered] == [
            "https://example.test/a",
            "https://example.test/b",
        ]
        assert all(item.source_id == source.id for item in discovered)
        db.refresh(source)
        assert source.discovered_url_count == 2
        assert source.last_checked_at is not None
    engine.dispose()


def test_inactive_source_cannot_enqueue_document(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path}/inactive.db")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        source = WebSource(
            domain="example.test",
            base_url="https://example.test/feed.xml",
            category="feed",
            access_method="feed",
            state="pending",
        )
        db.add(source)
        db.commit()
        with pytest.raises(DiscoveryDocumentError, match="inactive"):
            enqueue_discovery_document(db, Scan(), source, b"<rss><channel/></rss>")
    engine.dispose()
