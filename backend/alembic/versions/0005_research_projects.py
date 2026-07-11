"""add research projects

Revision ID: 0005_research_projects
Revises: 0004_mentor_runtime
Create Date: 2026-07-11 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_research_projects"
down_revision: str | None = "0004_mentor_runtime"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "research_projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("objective", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("context", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_research_projects_id", "research_projects", ["id"], unique=False)
    op.create_index("ix_research_projects_owner_id", "research_projects", ["owner_id"], unique=False)
    op.create_index("ix_research_projects_status", "research_projects", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_research_projects_status", table_name="research_projects")
    op.drop_index("ix_research_projects_owner_id", table_name="research_projects")
    op.drop_index("ix_research_projects_id", table_name="research_projects")
    op.drop_table("research_projects")
