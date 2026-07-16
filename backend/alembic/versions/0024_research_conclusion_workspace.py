"""add research conclusion workspace

Revision ID: 0024_research_conclusion_workspace
Revises: 0023_research_follow_up_tracker
Create Date: 2026-07-16 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0024_research_conclusion_workspace"
down_revision: str | None = "0023_research_follow_up_tracker"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "research_conclusions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("conclusion_text", sa.Text(), nullable=False),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.Column("finalized_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["research_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "project_id", name="uq_research_conclusion_owner_project"),
    )
    op.create_index("ix_research_conclusions_id", "research_conclusions", ["id"])
    op.create_index("ix_research_conclusions_owner_id", "research_conclusions", ["owner_id"])
    op.create_index("ix_research_conclusions_project_id", "research_conclusions", ["project_id"])
    op.create_index("ix_research_conclusions_status", "research_conclusions", ["status"])

    op.create_table(
        "research_conclusion_revisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conclusion_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("conclusion_text", sa.Text(), nullable=False),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.Column("revision_note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["conclusion_id"], ["research_conclusions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["research_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("conclusion_id", "revision_number", name="uq_research_conclusion_revision_number"),
    )
    op.create_index("ix_research_conclusion_revisions_id", "research_conclusion_revisions", ["id"])
    op.create_index("ix_research_conclusion_revisions_conclusion_id", "research_conclusion_revisions", ["conclusion_id"])
    op.create_index("ix_research_conclusion_revisions_owner_id", "research_conclusion_revisions", ["owner_id"])
    op.create_index("ix_research_conclusion_revisions_project_id", "research_conclusion_revisions", ["project_id"])
    op.create_index("ix_research_conclusion_revisions_status", "research_conclusion_revisions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_research_conclusion_revisions_status", table_name="research_conclusion_revisions")
    op.drop_index("ix_research_conclusion_revisions_project_id", table_name="research_conclusion_revisions")
    op.drop_index("ix_research_conclusion_revisions_owner_id", table_name="research_conclusion_revisions")
    op.drop_index("ix_research_conclusion_revisions_conclusion_id", table_name="research_conclusion_revisions")
    op.drop_index("ix_research_conclusion_revisions_id", table_name="research_conclusion_revisions")
    op.drop_table("research_conclusion_revisions")
    op.drop_index("ix_research_conclusions_status", table_name="research_conclusions")
    op.drop_index("ix_research_conclusions_project_id", table_name="research_conclusions")
    op.drop_index("ix_research_conclusions_owner_id", table_name="research_conclusions")
    op.drop_index("ix_research_conclusions_id", table_name="research_conclusions")
    op.drop_table("research_conclusions")
