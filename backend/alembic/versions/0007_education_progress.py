"""add education lesson progress

Revision ID: 0007_education_progress
Revises: 0006_research_sessions
Create Date: 2026-07-11 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_education_progress"
down_revision: str | None = "0006_research_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lesson_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("lesson_slug", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "lesson_slug", name="uq_lesson_progress_user_slug"),
    )
    op.create_index("ix_lesson_progress_user_id", "lesson_progress", ["user_id"], unique=False)
    op.create_index("ix_lesson_progress_lesson_slug", "lesson_progress", ["lesson_slug"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_lesson_progress_lesson_slug", table_name="lesson_progress")
    op.drop_index("ix_lesson_progress_user_id", table_name="lesson_progress")
    op.drop_table("lesson_progress")
