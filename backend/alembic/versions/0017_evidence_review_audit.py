"""add evidence review audit

Revision ID: 0017_evidence_review_audit
Revises: 0016_research_evidence
Create Date: 2026-07-15 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_evidence_review_audit"
down_revision: str | None = "0016_research_evidence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evidence_review_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("evidence_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("reviewer_id", sa.Integer(), nullable=False),
        sa.Column("previous_status", sa.String(length=24), nullable=False),
        sa.Column("validation_status", sa.String(length=24), nullable=False),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence_records.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evidence_review_events_evidence_id", "evidence_review_events", ["evidence_id"])
    op.create_index("ix_evidence_review_events_owner_id", "evidence_review_events", ["owner_id"])
    op.create_index("ix_evidence_review_events_reviewer_id", "evidence_review_events", ["reviewer_id"])
    op.create_index(
        "ix_evidence_review_events_validation_status",
        "evidence_review_events",
        ["validation_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_evidence_review_events_validation_status", table_name="evidence_review_events")
    op.drop_index("ix_evidence_review_events_reviewer_id", table_name="evidence_review_events")
    op.drop_index("ix_evidence_review_events_owner_id", table_name="evidence_review_events")
    op.drop_index("ix_evidence_review_events_evidence_id", table_name="evidence_review_events")
    op.drop_table("evidence_review_events")
