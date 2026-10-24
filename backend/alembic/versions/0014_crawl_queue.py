"""File persistante de découverte et de crawl.

Revision ID: 0014
Revises: 0013
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "discovered_urls",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "owner_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "scan_id", sa.String(36), sa.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("source_id", sa.String(36), sa.ForeignKey("web_sources.id", ondelete="SET NULL")),
        sa.Column("original_url", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("url_hash", sa.String(64), nullable=False),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column("discovery_method", sa.String(80), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("scan_id", "url_hash", name="uq_discovered_url_scan_hash"),
    )
    for name, columns in (
        ("ix_discovered_urls_owner_id", ["owner_id"]),
        ("ix_discovered_urls_scan_id", ["scan_id"]),
        ("ix_discovered_urls_source_id", ["source_id"]),
        ("ix_discovered_urls_domain", ["domain"]),
    ):
        op.create_index(name, "discovered_urls", columns)

    op.create_table(
        "crawl_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "owner_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "scan_id", sa.String(36), sa.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "discovered_url_id",
            sa.String(36),
            sa.ForeignKey("discovered_urls.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("lease_owner", sa.String(100)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("error_code", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("discovered_url_id"),
    )
    for name, columns in (
        ("ix_crawl_jobs_owner_id", ["owner_id"]),
        ("ix_crawl_jobs_scan_id", ["scan_id"]),
        ("ix_crawl_jobs_discovered_url_id", ["discovered_url_id"]),
        ("ix_crawl_jobs_status", ["status"]),
        ("ix_crawl_jobs_priority", ["priority"]),
        ("ix_crawl_jobs_next_attempt_at", ["next_attempt_at"]),
        ("ix_crawl_jobs_lease_owner", ["lease_owner"]),
        ("ix_crawl_jobs_lease_expires_at", ["lease_expires_at"]),
    ):
        op.create_index(name, "crawl_jobs", columns)

    op.create_table(
        "crawl_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "crawl_job_id",
            sa.String(36),
            sa.ForeignKey("crawl_jobs.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("http_status", sa.Integer()),
        sa.Column("final_url", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(255)),
        sa.Column("content_length", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(64)),
        sa.Column("extracted_text", sa.Text()),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cache_expires_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_crawl_results_crawl_job_id", "crawl_results", ["crawl_job_id"])
    op.create_index("ix_crawl_results_content_hash", "crawl_results", ["content_hash"])
    op.create_index("ix_crawl_results_cache_expires_at", "crawl_results", ["cache_expires_at"])

    op.create_table(
        "crawl_statistics",
        sa.Column(
            "scan_id",
            sa.String(36),
            sa.ForeignKey("scans.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("discovered_count", sa.Integer(), nullable=False),
        sa.Column("queued_count", sa.Integer(), nullable=False),
        sa.Column("fetched_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("bytes_downloaded", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("crawl_statistics")
    op.drop_table("crawl_results")
    op.drop_table("crawl_jobs")
    op.drop_table("discovered_urls")
