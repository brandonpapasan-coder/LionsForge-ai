"""add research follow-up tracker fields

Revision ID: 0023_research_follow_up_tracker
Revises: 0022_research_governance_digest
Create Date: 2026-07-16 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023_research_follow_up_tracker"
down_revision: str | None = "0022_research_governance_digest"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("research_review_actions", sa.Column("priority", sa.String(length=16), server_default="normal", nullable=False))
    op.add_column("research_review_actions", sa.Column("due_at", sa.DateTime(), nullable=True))
    op.add_column("research_review_actions", sa.Column("owner_notes", sa.Text(), nullable=True))
    op.add_column("research_review_actions", sa.Column("resolution_notes", sa.Text(), nullable=True))
    op.add_column("research_review_actions", sa.Column("resolved_at", sa.DateTime(), nullable=True))
    op.create_index("ix_research_review_actions_priority", "research_review_actions", ["priority"])
    op.create_index("ix_research_review_actions_due_at", "research_review_actions", ["due_at"])


def downgrade() -> None:
    op.drop_index("ix_research_review_actions_due_at", table_name="research_review_actions")
    op.drop_index("ix_research_review_actions_priority", table_name="research_review_actions")
    op.drop_column("research_review_actions", "resolved_at")
    op.drop_column("research_review_actions", "resolution_notes")
    op.drop_column("research_review_actions", "owner_notes")
    op.drop_column("research_review_actions", "due_at")
    op.drop_column("research_review_actions", "priority")
