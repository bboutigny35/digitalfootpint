"""Suivi local des demandes de suppression.

Revision ID: 0008
Revises: 0007
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    status_enum = sa.Enum(
        "DRAFT",
        "SENT",
        "ACKNOWLEDGED",
        "COMPLETED",
        "REJECTED",
        "CANCELLED",
        name="removalrequeststatus",
    )
    op.create_table(
        "removal_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("result_id", sa.String(length=36), nullable=True),
        sa.Column("organization", sa.String(length=255), nullable=False),
        sa.Column("status", status_enum, nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("response_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("response_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["result_id"], ["results.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_removal_requests_owner_id", "removal_requests", ["owner_id"])
    op.create_index("ix_removal_requests_result_id", "removal_requests", ["result_id"])
    op.create_index("ix_removal_requests_status", "removal_requests", ["status"])


def downgrade() -> None:
    op.drop_index("ix_removal_requests_status", table_name="removal_requests")
    op.drop_index("ix_removal_requests_result_id", table_name="removal_requests")
    op.drop_index("ix_removal_requests_owner_id", table_name="removal_requests")
    op.drop_table("removal_requests")
    if op.get_bind().dialect.name == "postgresql":
        sa.Enum(name="removalrequeststatus").drop(op.get_bind(), checkfirst=True)
