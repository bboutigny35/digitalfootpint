"""Index de purge des descripteurs sensibles.

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_sensitive_descriptors_retention_expires_at",
        "sensitive_descriptors",
        ["retention_expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_sensitive_descriptors_retention_expires_at",
        table_name="sensitive_descriptors",
    )
