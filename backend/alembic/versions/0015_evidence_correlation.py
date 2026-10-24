"""Preuves, corrélations et validations utilisateur.

Revision ID: 0015
Revises: 0014
"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "owner_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "scan_id", sa.String(36), sa.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("result_id", sa.String(36), sa.ForeignKey("results.id", ondelete="CASCADE")),
        sa.Column(
            "crawl_result_id", sa.String(36), sa.ForeignKey("crawl_results.id", ondelete="CASCADE")
        ),
        sa.Column("evidence_type", sa.String(80), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
    )
    for name, columns in (
        ("ix_evidence_owner_id", ["owner_id"]),
        ("ix_evidence_scan_id", ["scan_id"]),
        ("ix_evidence_result_id", ["result_id"]),
        ("ix_evidence_crawl_result_id", ["crawl_result_id"]),
        ("ix_evidence_evidence_type", ["evidence_type"]),
        ("ix_evidence_source_hash", ["source_hash"]),
    ):
        op.create_index(name, "evidence", columns)
    op.create_table(
        "evidence_matches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "evidence_id",
            sa.String(36),
            sa.ForeignKey("evidence.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("criterion_type", sa.String(80), nullable=False),
        sa.Column("criterion_hash", sa.String(64), nullable=False),
        sa.Column("match_kind", sa.String(40), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "evidence_id", "criterion_type", "criterion_hash", name="uq_evidence_match"
        ),
    )
    op.create_index("ix_evidence_matches_evidence_id", "evidence_matches", ["evidence_id"])
    op.create_index("ix_evidence_matches_criterion_type", "evidence_matches", ["criterion_type"])
    op.create_table(
        "identity_correlations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "owner_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "result_id",
            sa.String(36),
            sa.ForeignKey("results.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("relevance_score", sa.Float(), nullable=False),
        sa.Column("attribution_score", sa.Float(), nullable=False),
        sa.Column("explanation", sa.JSON(), nullable=False),
        sa.Column("contradictions", sa.JSON(), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_identity_correlations_owner_id", "identity_correlations", ["owner_id"])
    op.create_index("ix_identity_correlations_result_id", "identity_correlations", ["result_id"])
    op.create_table(
        "user_validations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "owner_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "correlation_id",
            sa.String(36),
            sa.ForeignKey("identity_correlations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("decision", sa.String(30), nullable=False),
        sa.Column("exclusion_kind", sa.String(80)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("owner_id", "correlation_id", name="uq_user_validation_correlation"),
    )
    op.create_index("ix_user_validations_owner_id", "user_validations", ["owner_id"])
    op.create_index("ix_user_validations_correlation_id", "user_validations", ["correlation_id"])
    op.create_index("ix_user_validations_decision", "user_validations", ["decision"])


def downgrade() -> None:
    op.drop_table("user_validations")
    op.drop_table("identity_correlations")
    op.drop_table("evidence_matches")
    op.drop_table("evidence")
