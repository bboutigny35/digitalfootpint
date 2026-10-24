"""Enrichissement additif des profils d'identité.

Revision ID: 0012
Revises: 0011
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("identity_profiles") as batch:
        batch.add_column(
            sa.Column("former_pseudonyms", sa.JSON(), nullable=False, server_default="[]")
        )
        batch.add_column(
            sa.Column("phone_numbers", sa.JSON(), nullable=False, server_default="[]")
        )
        batch.add_column(sa.Column("city_region", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("profession", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("employers", sa.JSON(), nullable=False, server_default="[]"))
        batch.add_column(
            sa.Column("confirmed_profiles", sa.JSON(), nullable=False, server_default="[]")
        )
        batch.add_column(
            sa.Column("exact_phrases", sa.JSON(), nullable=False, server_default="[]")
        )
        batch.add_column(sa.Column("exclusions", sa.JSON(), nullable=False, server_default="[]"))


def downgrade() -> None:
    with op.batch_alter_table("identity_profiles") as batch:
        batch.drop_column("exclusions")
        batch.drop_column("exact_phrases")
        batch.drop_column("confirmed_profiles")
        batch.drop_column("employers")
        batch.drop_column("profession")
        batch.drop_column("city_region")
        batch.drop_column("phone_numbers")
        batch.drop_column("former_pseudonyms")
