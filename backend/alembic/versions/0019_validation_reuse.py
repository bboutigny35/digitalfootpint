"""Correction d'attribution et réutilisation privée des validations.

Revision ID: 0019
Revises: 0018
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("user_validations") as batch_op:
        batch_op.add_column(sa.Column("attributed_profile_id", sa.String(36)))
        batch_op.add_column(sa.Column("reused_from_validation_id", sa.String(36)))
        batch_op.create_foreign_key(
            "fk_user_validation_attributed_profile",
            "identity_profiles",
            ["attributed_profile_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_user_validation_reused_from",
            "user_validations",
            ["reused_from_validation_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_user_validations_attributed_profile_id", ["attributed_profile_id"]
        )
        batch_op.create_index(
            "ix_user_validations_reused_from_validation_id",
            ["reused_from_validation_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("user_validations") as batch_op:
        batch_op.drop_index("ix_user_validations_reused_from_validation_id")
        batch_op.drop_index("ix_user_validations_attributed_profile_id")
        batch_op.drop_constraint("fk_user_validation_reused_from", type_="foreignkey")
        batch_op.drop_constraint("fk_user_validation_attributed_profile", type_="foreignkey")
        batch_op.drop_column("reused_from_validation_id")
        batch_op.drop_column("attributed_profile_id")
