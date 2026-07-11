"""add research sessions

Revision ID: 0006_research_sessions
Revises: 0005_research_projects
Create Date: 2026-07-11 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_research_sessions"
down_revision: str | None = "0005_research_projects"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "research_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("objective", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("context", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["research_projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_research_sessions_id", "research_sessions", ["id"], unique=False)
    op.create_index("ix_research_sessions_project_id", "research_sessions", ["project_id"], unique=False)
    op.create_index("ix_research_sessions_status", "research_sessions", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_research_sessions_status", table_name="research_sessions")
    op.drop_index("ix_research_sessions_project_id", table_name="research_sessions")
    op.drop_index("ix_research_sessions_id", table_name="research_sessions")
    op.drop_table("research_sessions")
