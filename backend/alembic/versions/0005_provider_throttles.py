"""Rate limiting partagé des fournisseurs.

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provider_throttles",
        sa.Column("connector_id", sa.String(length=100), nullable=False),
        sa.Column("next_request_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("connector_id"),
    )
    op.create_index(
        "ix_provider_throttles_next_request_at",
        "provider_throttles",
        ["next_request_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_provider_throttles_next_request_at", table_name="provider_throttles")
    op.drop_table("provider_throttles")
