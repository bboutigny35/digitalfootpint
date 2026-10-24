"""Coffre chiffré des secrets de connecteurs.

Revision ID: 0010
Revises: 0009
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "connector_secrets",
        sa.Column("connector_id", sa.String(length=100), nullable=False),
        sa.Column("ciphertext", sa.Text(), nullable=False),
        sa.Column("key_version", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("connector_id"),
    )
    op.create_index(
        "ix_connector_secrets_key_version",
        "connector_secrets",
        ["key_version"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_connector_secrets_key_version", table_name="connector_secrets")
    op.drop_table("connector_secrets")
