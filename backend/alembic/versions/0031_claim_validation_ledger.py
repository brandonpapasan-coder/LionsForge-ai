"""add append-only claim validation ledger

Revision ID: 0031_claim_validation_ledger
Revises: 0030_evidence_assessment
Create Date: 2026-07-19 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0031_claim_validation_ledger"
down_revision: str | None = "0030_evidence_assessment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "claim_validation_judgments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("claim_id", sa.Integer(), nullable=False),
        sa.Column("reviewer_id", sa.Integer(), nullable=False),
        sa.Column("validation_status", sa.String(length=24), nullable=False),
        sa.Column("confidence_level", sa.String(length=24), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("unresolved_questions", sa.Text(), nullable=True),
        sa.Column("claim_updated_at_snapshot", sa.DateTime(), nullable=False),
        sa.Column("evidence_updated_at_snapshot", sa.DateTime(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["investigation_claims.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_claim_validation_judgments_id"), "claim_validation_judgments", ["id"], unique=False)
    op.create_index(op.f("ix_claim_validation_judgments_claim_id"), "claim_validation_judgments", ["claim_id"], unique=False)
    op.create_index(op.f("ix_claim_validation_judgments_reviewer_id"), "claim_validation_judgments", ["reviewer_id"], unique=False)
    op.create_index(op.f("ix_claim_validation_judgments_validation_status"), "claim_validation_judgments", ["validation_status"], unique=False)
    op.create_index(op.f("ix_claim_validation_judgments_confidence_level"), "claim_validation_judgments", ["confidence_level"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_claim_validation_judgments_confidence_level"), table_name="claim_validation_judgments")
    op.drop_index(op.f("ix_claim_validation_judgments_validation_status"), table_name="claim_validation_judgments")
    op.drop_index(op.f("ix_claim_validation_judgments_reviewer_id"), table_name="claim_validation_judgments")
    op.drop_index(op.f("ix_claim_validation_judgments_claim_id"), table_name="claim_validation_judgments")
    op.drop_index(op.f("ix_claim_validation_judgments_id"), table_name="claim_validation_judgments")
    op.drop_table("claim_validation_judgments")
