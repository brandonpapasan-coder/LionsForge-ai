"""persist adaptive assessment attempt history

Revision ID: 0027_assessment_attempt_history
Revises: 0026_user_authored_memory
Create Date: 2026-07-19 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0027_assessment_attempt_history"
down_revision: str | None = "0026_user_authored_memory"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assessment_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("lesson_slug", sa.String(length=120), nullable=False),
        sa.Column("competency", sa.String(length=120), nullable=False),
        sa.Column("difficulty", sa.String(length=24), nullable=False),
        sa.Column("question_id", sa.String(length=120), nullable=False),
        sa.Column("selected_option", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assessment_attempts_user_id"), "assessment_attempts", ["user_id"], unique=False)
    op.create_index(op.f("ix_assessment_attempts_lesson_slug"), "assessment_attempts", ["lesson_slug"], unique=False)
    op.create_index(op.f("ix_assessment_attempts_competency"), "assessment_attempts", ["competency"], unique=False)
    op.create_index(op.f("ix_assessment_attempts_created_at"), "assessment_attempts", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_assessment_attempts_created_at"), table_name="assessment_attempts")
    op.drop_index(op.f("ix_assessment_attempts_competency"), table_name="assessment_attempts")
    op.drop_index(op.f("ix_assessment_attempts_lesson_slug"), table_name="assessment_attempts")
    op.drop_index(op.f("ix_assessment_attempts_user_id"), table_name="assessment_attempts")
    op.drop_table("assessment_attempts")
