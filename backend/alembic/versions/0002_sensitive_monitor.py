"""Module de surveillance des données sensibles.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

category_enum = sa.Enum(
    "NIR",
    "PAYMENT_CARD",
    "IBAN",
    "PHONE",
    "POSTAL_ADDRESS",
    "ID_DOCUMENT",
    name="sensitivecategory",
)
check_status_enum = sa.Enum("PENDING", "COMPLETED", "FAILED", name="checkstatus")
risk_enum = sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="risklevel")
finding_enum = sa.Enum("CONFIRMED", "NEEDS_REVIEW", "FALSE_POSITIVE", name="findingstatus")


def upgrade() -> None:
    op.create_table(
        "sensitive_descriptors",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "owner_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("category", category_enum, nullable=False),
        sa.Column("masked_label", sa.String(160), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("retention_expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sensitive_descriptors_owner_id", "sensitive_descriptors", ["owner_id"])
    op.create_index("ix_sensitive_descriptors_category", "sensitive_descriptors", ["category"])
    op.create_index(
        "ix_sensitive_owner_fingerprint",
        "sensitive_descriptors",
        ["owner_id", "fingerprint"],
        unique=True,
    )
    op.create_table(
        "sensitive_consents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "owner_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("provider_id", sa.String(100), nullable=False),
        sa.Column("category", category_enum, nullable=False),
        sa.Column("authorization_confirmed", sa.Boolean(), nullable=False),
        sa.Column("proof_reference", sa.String(200)),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_sensitive_consents_owner_id", "sensitive_consents", ["owner_id"])
    op.create_index("ix_sensitive_consents_provider_id", "sensitive_consents", ["provider_id"])
    op.create_table(
        "sensitive_checks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "owner_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "descriptor_id",
            sa.String(36),
            sa.ForeignKey("sensitive_descriptors.id", ondelete="SET NULL"),
        ),
        sa.Column("category", category_enum, nullable=False),
        sa.Column("provider_id", sa.String(100), nullable=False),
        sa.Column("status", check_status_enum, nullable=False),
        sa.Column("external_transmission", sa.Boolean(), nullable=False),
        sa.Column("error_code", sa.String(100)),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_sensitive_checks_owner_id", "sensitive_checks", ["owner_id"])
    op.create_index("ix_sensitive_checks_descriptor_id", "sensitive_checks", ["descriptor_id"])
    op.create_index("ix_sensitive_checks_category", "sensitive_checks", ["category"])
    op.create_table(
        "sensitive_findings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "owner_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "check_id",
            sa.String(36),
            sa.ForeignKey("sensitive_checks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category", category_enum, nullable=False),
        sa.Column("source_label", sa.String(160), nullable=False),
        sa.Column("risk_level", risk_enum, nullable=False),
        sa.Column("verification_status", finding_enum, nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sensitive_findings_owner_id", "sensitive_findings", ["owner_id"])
    op.create_index("ix_sensitive_findings_check_id", "sensitive_findings", ["check_id"])
    op.create_table(
        "sensitive_alerts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "owner_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "finding_id",
            sa.String(36),
            sa.ForeignKey("sensitive_findings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category", category_enum, nullable=False),
        sa.Column("source_label", sa.String(160), nullable=False),
        sa.Column("risk_level", risk_enum, nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_sensitive_alerts_owner_id", "sensitive_alerts", ["owner_id"])
    op.create_index("ix_sensitive_alerts_finding_id", "sensitive_alerts", ["finding_id"])


def downgrade() -> None:
    for table in (
        "sensitive_alerts",
        "sensitive_findings",
        "sensitive_checks",
        "sensitive_consents",
        "sensitive_descriptors",
    ):
        op.drop_table(table)
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for enum_name in ("findingstatus", "risklevel", "checkstatus", "sensitivecategory"):
            sa.Enum(name=enum_name).drop(bind, checkfirst=True)
