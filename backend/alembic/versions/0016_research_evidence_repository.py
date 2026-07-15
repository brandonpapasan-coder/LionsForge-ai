"""add research evidence repository

Revision ID: 0016_research_evidence
Revises: 0015_research_planning
Create Date: 2026-07-14 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_research_evidence"
down_revision: str | None = "0015_research_planning"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "research_evidence",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_reference", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["research_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["research_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_research_evidence_project_id", "research_evidence", ["project_id"])
    op.create_index("ix_research_evidence_session_id", "research_evidence", ["session_id"])
    op.create_index("ix_research_evidence_source_type", "research_evidence", ["source_type"])
    op.create_index("ix_research_evidence_status", "research_evidence", ["status"])


def downgrade() -> None:
    op.drop_index("ix_research_evidence_status", table_name="research_evidence")
    op.drop_index("ix_research_evidence_source_type", table_name="research_evidence")
    op.drop_index("ix_research_evidence_session_id", table_name="research_evidence")
    op.drop_index("ix_research_evidence_project_id", table_name="research_evidence")
    op.drop_table("research_evidence")
