"""add evidence assessment fields

Revision ID: 0030_evidence_assessment
Revises: 0029_claims_evidence
Create Date: 2026-07-19 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0030_evidence_assessment"
down_revision: str | None = "0029_claims_evidence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("investigation_claims", sa.Column("confidence_level", sa.String(length=24), nullable=True))
    op.add_column("investigation_claims", sa.Column("confidence_rationale", sa.Text(), nullable=True))
    op.create_index(
        op.f("ix_investigation_claims_confidence_level"),
        "investigation_claims",
        ["confidence_level"],
        unique=False,
    )
    op.add_column("claim_evidence", sa.Column("credibility_rating", sa.String(length=24), nullable=True))
    op.add_column("claim_evidence", sa.Column("credibility_rationale", sa.Text(), nullable=True))
    op.create_index(
        op.f("ix_claim_evidence_credibility_rating"),
        "claim_evidence",
        ["credibility_rating"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_claim_evidence_credibility_rating"), table_name="claim_evidence")
    op.drop_column("claim_evidence", "credibility_rationale")
    op.drop_column("claim_evidence", "credibility_rating")
    op.drop_index(op.f("ix_investigation_claims_confidence_level"), table_name="investigation_claims")
    op.drop_column("investigation_claims", "confidence_rationale")
    op.drop_column("investigation_claims", "confidence_level")