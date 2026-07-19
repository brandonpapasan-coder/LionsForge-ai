"""add investigation claims and evidence

Revision ID: 0029_investigation_claims_evidence
Revises: 0028_investigation_foundation
Create Date: 2026-07-19 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0029_investigation_claims_evidence"
down_revision: str | None = "0028_investigation_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "investigation_claims",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("investigation_id", sa.Integer(), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_investigation_claims_investigation_id"),
        "investigation_claims",
        ["investigation_id"],
        unique=False,
    )

    op.create_table(
        "claim_evidence",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("claim_id", sa.Integer(), nullable=False),
        sa.Column("source_title", sa.String(length=240), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("evidence_type", sa.String(length=24), nullable=False),
        sa.Column("relationship", sa.String(length=24), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["investigation_claims.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_claim_evidence_claim_id"), "claim_evidence", ["claim_id"], unique=False)
    op.create_index(op.f("ix_claim_evidence_evidence_type"), "claim_evidence", ["evidence_type"], unique=False)
    op.create_index(op.f("ix_claim_evidence_relationship"), "claim_evidence", ["relationship"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_claim_evidence_relationship"), table_name="claim_evidence")
    op.drop_index(op.f("ix_claim_evidence_evidence_type"), table_name="claim_evidence")
    op.drop_index(op.f("ix_claim_evidence_claim_id"), table_name="claim_evidence")
    op.drop_table("claim_evidence")
    op.drop_index(op.f("ix_investigation_claims_investigation_id"), table_name="investigation_claims")
    op.drop_table("investigation_claims")
