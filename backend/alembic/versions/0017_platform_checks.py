"""Résultats normalisés de vérification des plateformes.

Revision ID: 0017
Revises: 0016
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "platform_check_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "owner_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "scan_id", sa.String(36), sa.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "platform_identifier",
            sa.String(100),
            sa.ForeignKey("platform_catalog.identifier", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("connector_id", sa.String(100)),
        sa.Column("verification_method", sa.String(80), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("result_count", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(100)),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "scan_id", "platform_identifier", name="uq_platform_check_scan_platform"
        ),
    )
    for name, columns in (
        ("ix_platform_check_results_owner_id", ["owner_id"]),
        ("ix_platform_check_results_scan_id", ["scan_id"]),
        ("ix_platform_check_results_platform_identifier", ["platform_identifier"]),
        ("ix_platform_check_results_status", ["status"]),
    ):
        op.create_index(name, "platform_check_results", columns)


def downgrade() -> None:
    op.drop_table("platform_check_results")
