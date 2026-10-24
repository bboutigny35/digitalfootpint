"""Rattache Bluesky à son connecteur officiel.

Revision ID: 0018
Revises: 0017
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

platform_catalog = sa.table(
    "platform_catalog",
    sa.column("identifier", sa.String()),
    sa.column("connector_id", sa.String()),
    sa.column("verification_method", sa.String()),
    sa.column("default_status", sa.String()),
)


def upgrade() -> None:
    op.execute(
        sa.update(platform_catalog)
        .where(platform_catalog.c.identifier == "bluesky")
        .values(
            connector_id="bluesky",
            verification_method="official_api",
            default_status="NO_PUBLIC_RESULT",
        )
    )


def downgrade() -> None:
    op.execute(
        sa.update(platform_catalog)
        .where(platform_catalog.c.identifier == "bluesky")
        .values(
            connector_id=None,
            verification_method="public_profile",
            default_status="NO_PUBLIC_RESULT",
        )
    )
