"""Baux persistants et reprises des scans.

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("scans") as batch:
        batch.add_column(
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(sa.Column("lease_owner", sa.String(length=100), nullable=True))
        batch.add_column(sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_index("ix_scans_lease_owner", ["lease_owner"])
        batch.create_index("ix_scans_lease_expires_at", ["lease_expires_at"])
        batch.create_index("ix_scans_next_attempt_at", ["next_attempt_at"])


def downgrade() -> None:
    with op.batch_alter_table("scans") as batch:
        batch.drop_index("ix_scans_next_attempt_at")
        batch.drop_index("ix_scans_lease_expires_at")
        batch.drop_index("ix_scans_lease_owner")
        batch.drop_column("next_attempt_at")
        batch.drop_column("lease_expires_at")
        batch.drop_column("lease_owner")
        batch.drop_column("attempt_count")
