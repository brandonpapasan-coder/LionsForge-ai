"""add research governance digest preferences and snapshots

Revision ID: 0022_research_governance_digest
Revises: 0021_research_review_actions
Create Date: 2026-07-16 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022_research_governance_digest"
down_revision: str | None = "0021_research_review_actions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "research_governance_digest_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("project_ids", sa.JSON(), nullable=False),
        sa.Column("impact_levels", sa.JSON(), nullable=False),
        sa.Column("window_days", sa.Integer(), nullable=False),
        sa.Column("cadence", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", name="uq_research_governance_digest_preference_owner"),
    )
    op.create_index("ix_research_governance_digest_preferences_id", "research_governance_digest_preferences", ["id"])
    op.create_index("ix_research_governance_digest_preferences_owner_id", "research_governance_digest_preferences", ["owner_id"])

    op.create_table(
        "research_governance_digest_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("preference_id", sa.Integer(), nullable=True),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("window_start", sa.DateTime(), nullable=False),
        sa.Column("window_end", sa.DateTime(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("item_count", sa.Integer(), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["preference_id"], ["research_governance_digest_preferences.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("id", "owner_id", "preference_id", "generated_at", "content_sha256"):
        op.create_index(f"ix_research_governance_digest_snapshots_{column}", "research_governance_digest_snapshots", [column])


def downgrade() -> None:
    for column in ("content_sha256", "generated_at", "preference_id", "owner_id", "id"):
        op.drop_index(f"ix_research_governance_digest_snapshots_{column}", table_name="research_governance_digest_snapshots")
    op.drop_table("research_governance_digest_snapshots")
    op.drop_index("ix_research_governance_digest_preferences_owner_id", table_name="research_governance_digest_preferences")
    op.drop_index("ix_research_governance_digest_preferences_id", table_name="research_governance_digest_preferences")
    op.drop_table("research_governance_digest_preferences")
