"""add research planning engine

Revision ID: 0015_research_planning
Revises: 0014_knowledge_federation
Create Date: 2026-07-13 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_research_planning"
down_revision: str | None = "0014_knowledge_federation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "research_plan_recommendations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("recommendation_type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("recommended_action", sa.Text(), nullable=False),
        sa.Column("priority_score", sa.Float(), nullable=False),
        sa.Column("priority_components", sa.JSON(), nullable=False),
        sa.Column("source_memory_ids", sa.JSON(), nullable=False),
        sa.Column("source_evidence_ids", sa.JSON(), nullable=False),
        sa.Column("source_federation_link_ids", sa.JSON(), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("mission_id", sa.Integer(), nullable=True),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["mission_id"], ["missions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["research_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "fingerprint", name="uq_research_plan_recommendation"),
    )
    for column in ("id", "owner_id", "project_id", "recommendation_type", "priority_score", "status", "fingerprint"):
        op.create_index(f"ix_research_plan_recommendations_{column}", "research_plan_recommendations", [column])

    op.create_table(
        "research_plan_revisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recommendation_id", sa.Integer(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("recommendation_type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("recommended_action", sa.Text(), nullable=False),
        sa.Column("priority_score", sa.Float(), nullable=False),
        sa.Column("priority_components", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("mission_id", sa.Integer(), nullable=True),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["recommendation_id"], ["research_plan_recommendations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recommendation_id", "revision_number", name="uq_research_plan_revision"),
    )
    op.create_index("ix_research_plan_revisions_id", "research_plan_revisions", ["id"])
    op.create_index("ix_research_plan_revisions_recommendation_id", "research_plan_revisions", ["recommendation_id"])


def downgrade() -> None:
    op.drop_index("ix_research_plan_revisions_recommendation_id", table_name="research_plan_revisions")
    op.drop_index("ix_research_plan_revisions_id", table_name="research_plan_revisions")
    op.drop_table("research_plan_revisions")
    for column in reversed(("id", "owner_id", "project_id", "recommendation_type", "priority_score", "status", "fingerprint")):
        op.drop_index(f"ix_research_plan_recommendations_{column}", table_name="research_plan_recommendations")
    op.drop_table("research_plan_recommendations")
