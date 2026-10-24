"""Tâches persistantes de découverte par campagne et source.

Revision ID: 0016
Revises: 0015
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "discovery_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "owner_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "scan_id", sa.String(36), sa.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "source_id",
            sa.String(36),
            sa.ForeignKey("web_sources.id", ondelete="CASCADE"),
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
        sa.UniqueConstraint("scan_id", "source_id", name="uq_discovery_job_scan_source"),
    )
    for name, columns in (
        ("ix_discovery_jobs_owner_id", ["owner_id"]),
        ("ix_discovery_jobs_scan_id", ["scan_id"]),
        ("ix_discovery_jobs_source_id", ["source_id"]),
        ("ix_discovery_jobs_status", ["status"]),
        ("ix_discovery_jobs_priority", ["priority"]),
        ("ix_discovery_jobs_next_attempt_at", ["next_attempt_at"]),
        ("ix_discovery_jobs_lease_owner", ["lease_owner"]),
        ("ix_discovery_jobs_lease_expires_at", ["lease_expires_at"]),
    ):
        op.create_index(name, "discovery_jobs", columns)


def downgrade() -> None:
    op.drop_table("discovery_jobs")
