"""Registre des sources Web et catalogue des plateformes.

Revision ID: 0013
Revises: 0012
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PLATFORMS = (
    ("github", "GitHub", "development", "official_api", "NO_PUBLIC_RESULT", "github", 10),
    ("gitlab", "GitLab", "development", "public_profile", "NO_PUBLIC_RESULT", "gitlab", 20),
    ("facebook", "Facebook", "social", "public_index", "NOT_VERIFIABLE", None, 100),
    ("instagram", "Instagram", "social", "public_index", "NOT_VERIFIABLE", None, 100),
    ("linkedin", "LinkedIn", "professional", "public_index", "NOT_VERIFIABLE", None, 100),
    ("x", "X", "social", "public_index", "NOT_VERIFIABLE", None, 100),
    ("tiktok", "TikTok", "social", "public_index", "NOT_VERIFIABLE", None, 100),
    ("threads", "Threads", "social", "public_index", "NOT_VERIFIABLE", None, 100),
    ("bluesky", "Bluesky", "social", "official_api", "NO_PUBLIC_RESULT", "bluesky", 70),
    ("mastodon", "Mastodon", "social", "public_profile", "NO_PUBLIC_RESULT", None, 70),
    ("reddit", "Reddit", "community", "public_profile", "NO_PUBLIC_RESULT", None, 70),
    ("youtube", "YouTube", "media", "public_profile", "NO_PUBLIC_RESULT", None, 70),
    ("twitch", "Twitch", "media", "public_profile", "NO_PUBLIC_RESULT", None, 70),
    ("discord", "Discord", "community", "user_verification", "NOT_VERIFIABLE", None, 120),
    ("amazon", "Amazon", "commerce", "public_index", "NOT_VERIFIABLE", None, 120),
    ("ebay", "eBay", "commerce", "public_index", "NOT_VERIFIABLE", None, 100),
    ("etsy", "Etsy", "commerce", "public_profile", "NO_PUBLIC_RESULT", None, 90),
    ("vinted", "Vinted", "commerce", "public_profile", "NO_PUBLIC_RESULT", None, 90),
    ("leboncoin", "Leboncoin", "commerce", "public_index", "NOT_VERIFIABLE", None, 110),
    ("netflix", "Netflix", "streaming", "none", "NOT_VERIFIABLE", None, 200),
    ("spotify", "Spotify", "streaming", "public_profile", "NO_PUBLIC_RESULT", None, 90),
    ("deezer", "Deezer", "streaming", "public_profile", "NO_PUBLIC_RESULT", None, 90),
    ("disney_plus", "Disney+", "streaming", "none", "NOT_VERIFIABLE", None, 200),
    ("stackoverflow", "Stack Overflow", "development", "public_profile", "NO_PUBLIC_RESULT", None, 60),
    ("dockerhub", "Docker Hub", "development", "public_profile", "NO_PUBLIC_RESULT", None, 60),
    ("npm", "npm", "development", "official_api", "NO_PUBLIC_RESULT", None, 50),
    ("pypi", "PyPI", "development", "official_api", "NO_PUBLIC_RESULT", None, 50),
    ("steam", "Steam", "gaming", "public_profile", "NO_PUBLIC_RESULT", None, 90),
    ("xbox", "Xbox", "gaming", "user_verification", "NOT_VERIFIABLE", None, 120),
    ("playstation", "PlayStation", "gaming", "user_verification", "NOT_VERIFIABLE", None, 120),
    ("epic_games", "Epic Games", "gaming", "none", "NOT_VERIFIABLE", None, 150),
    ("gravatar", "Gravatar", "identity", "official_api", "NO_PUBLIC_RESULT", None, 40),
)


def upgrade() -> None:
    op.create_table(
        "platform_catalog",
        sa.Column("identifier", sa.String(length=100), primary_key=True),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("verification_method", sa.String(length=80), nullable=False),
        sa.Column("default_status", sa.String(length=40), nullable=False),
        sa.Column("connector_id", sa.String(length=100), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("limitations", sa.Text(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_platform_catalog_category", "platform_catalog", ["category"])
    op.create_index("ix_platform_catalog_connector_id", "platform_catalog", ["connector_id"])
    now = datetime.now(UTC)
    table = sa.table(
        "platform_catalog",
        sa.column("identifier", sa.String()),
        sa.column("display_name", sa.String()),
        sa.column("category", sa.String()),
        sa.column("verification_method", sa.String()),
        sa.column("default_status", sa.String()),
        sa.column("connector_id", sa.String()),
        sa.column("priority", sa.Integer()),
        sa.column("limitations", sa.Text()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        table,
        [
            {
                "identifier": identifier,
                "display_name": name,
                "category": category,
                "verification_method": method,
                "default_status": status,
                "connector_id": connector,
                "priority": priority,
                "limitations": "Aucune énumération de comptes ni contournement d'accès.",
                "created_at": now,
                "updated_at": now,
            }
            for identifier, name, category, method, status, connector, priority in PLATFORMS
        ],
    )
    op.create_table(
        "web_sources",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("access_method", sa.String(length=80), nullable=False),
        sa.Column("state", sa.String(length=40), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("cache_ttl_seconds", sa.Integer(), nullable=False),
        sa.Column("rate_limit_per_minute", sa.Integer(), nullable=False),
        sa.Column("restrictions", sa.JSON(), nullable=False),
        sa.Column("discovered_url_count", sa.Integer(), nullable=False),
        sa.Column("crawled_page_count", sa.Integer(), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("domain"),
    )
    op.create_index("ix_web_sources_domain", "web_sources", ["domain"], unique=True)
    op.create_index("ix_web_sources_category", "web_sources", ["category"])
    op.create_index("ix_web_sources_state", "web_sources", ["state"])


def downgrade() -> None:
    op.drop_table("web_sources")
    op.drop_table("platform_catalog")
