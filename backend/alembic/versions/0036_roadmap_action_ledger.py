"""add roadmap action ledger persistence

Revision ID: 0036_roadmap_action_ledger
Revises: 0035_research_practicum
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0036_roadmap_action_ledger"
down_revision: str | None = "0035_research_practicum"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "roadmap_action_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("learner_user_id", sa.Integer(), nullable=False),
        sa.Column("enrollment_id", sa.Integer(), nullable=False),
        sa.Column("template_slug", sa.String(length=120), nullable=False),
        sa.Column("template_version", sa.Integer(), nullable=False),
        sa.Column("research_project_id", sa.Integer(), nullable=False),
        sa.Column("recommendation_reason_codes", sa.JSON(), nullable=False),
        sa.Column("roadmap_plan_sha256", sa.String(length=64), nullable=False),
        sa.Column("portfolio_sha256", sa.String(length=64), nullable=False),
        sa.Column("action_sha256", sa.String(length=64), nullable=False),
        sa.Column("action_receipt_sha256", sa.String(length=64), nullable=False),
        sa.Column("action_schema_version", sa.Integer(), nullable=False),
        sa.Column("action_generator_version", sa.String(length=32), nullable=False),
        sa.Column("acted_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["learner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["enrollment_id"], ["practicum_enrollments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["research_project_id"], ["research_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("enrollment_id", name="uq_roadmap_action_record_enrollment"),
    )
    for column in ("learner_user_id", "enrollment_id", "template_slug", "research_project_id", "acted_at"):
        op.create_index(op.f(f"ix_roadmap_action_records_{column}"), "roadmap_action_records", [column], unique=False)


def downgrade() -> None:
    for column in ("acted_at", "research_project_id", "template_slug", "enrollment_id", "learner_user_id"):
        op.drop_index(op.f(f"ix_roadmap_action_records_{column}"), table_name="roadmap_action_records")
    op.drop_table("roadmap_action_records")
