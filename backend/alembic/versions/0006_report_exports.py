"""Historique minimisé des exports.

Revision ID: 0006
Revises: 0005
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "report_exports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=True),
        sa.Column("export_format", sa.String(length=10), nullable=False),
        sa.Column("report_kind", sa.String(length=20), nullable=False),
        sa.Column("result_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["identity_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_report_exports_owner_id", "report_exports", ["owner_id"])
    op.create_index("ix_report_exports_profile_id", "report_exports", ["profile_id"])
    op.create_index("ix_report_exports_created_at", "report_exports", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_report_exports_created_at", table_name="report_exports")
    op.drop_index("ix_report_exports_profile_id", table_name="report_exports")
    op.drop_index("ix_report_exports_owner_id", table_name="report_exports")
    op.drop_table("report_exports")
