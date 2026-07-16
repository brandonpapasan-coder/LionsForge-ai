"""add research review action queue

Revision ID: 0021_research_review_actions
Revises: 0020_market_learning_evidence
Create Date: 2026-07-16 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021_research_review_actions"
down_revision: str | None = "0020_market_learning_evidence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "research_review_actions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("evidence_id", sa.Integer(), nullable=False),
        sa.Column("action_key", sa.String(length=64), nullable=False),
        sa.Column("impact_level", sa.String(length=24), nullable=False),
        sa.Column("governing_rule", sa.String(length=80), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("action_text", sa.Text(), nullable=False),
        sa.Column("supporting_event_ids", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["research_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "action_key", name="uq_research_review_action_owner_key"),
    )
    for column in ("id", "owner_id", "project_id", "evidence_id", "action_key", "impact_level", "governing_rule", "status"):
        op.create_index(f"ix_research_review_actions_{column}", "research_review_actions", [column])

    op.create_table(
        "research_review_action_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("action_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("previous_status", sa.String(length=24), nullable=False),
        sa.Column("new_status", sa.String(length=24), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["action_id"], ["research_review_actions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("id", "action_id", "owner_id", "new_status"):
        op.create_index(f"ix_research_review_action_history_{column}", "research_review_action_history", [column])


def downgrade() -> None:
    for column in ("new_status", "owner_id", "action_id", "id"):
        op.drop_index(f"ix_research_review_action_history_{column}", table_name="research_review_action_history")
    op.drop_table("research_review_action_history")
    for column in ("status", "governing_rule", "impact_level", "action_key", "evidence_id", "project_id", "owner_id", "id"):
        op.drop_index(f"ix_research_review_actions_{column}", table_name="research_review_actions")
    op.drop_table("research_review_actions")
