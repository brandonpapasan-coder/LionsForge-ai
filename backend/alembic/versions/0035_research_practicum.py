"""add research practicum persistence

Revision ID: 0035_research_practicum
Revises: 0034_remediation_history
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0035_research_practicum"
down_revision: str | None = "0034_remediation_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "practicum_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("estimated_minutes", sa.Integer(), nullable=False),
        sa.Column("prerequisite_lesson_slugs", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", "version", name="uq_practicum_template_slug_version"),
    )
    op.create_index(op.f("ix_practicum_templates_slug"), "practicum_templates", ["slug"], unique=False)
    op.create_index(op.f("ix_practicum_templates_status"), "practicum_templates", ["status"], unique=False)

    op.create_table(
        "practicum_objectives",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("objective_key", sa.String(length=120), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("competency", sa.String(length=120), nullable=False),
        sa.Column("required_evidence_categories", sa.JSON(), nullable=False),
        sa.Column("minimum_evidence_count", sa.Integer(), nullable=False),
        sa.Column("reflection_required", sa.Boolean(), nullable=False),
        sa.Column("human_review_required", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["template_id"], ["practicum_templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("template_id", "objective_key", name="uq_practicum_objective_template_key"),
        sa.UniqueConstraint("template_id", "sequence", name="uq_practicum_objective_template_sequence"),
    )
    op.create_index(
        op.f("ix_practicum_objectives_template_id"), "practicum_objectives", ["template_id"], unique=False
    )
    op.create_index(
        op.f("ix_practicum_objectives_competency"), "practicum_objectives", ["competency"], unique=False
    )

    op.create_table(
        "practicum_enrollments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("template_version", sa.Integer(), nullable=False),
        sa.Column("research_project_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("submitted_for_review_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["research_project_id"], ["research_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["practicum_templates.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "template_id", "research_project_id", name="uq_practicum_enrollment_user_template_project"
        ),
    )
    for column in ("user_id", "template_id", "research_project_id", "status"):
        op.create_index(op.f(f"ix_practicum_enrollments_{column}"), "practicum_enrollments", [column], unique=False)

    op.create_table(
        "practicum_objective_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("enrollment_id", sa.Integer(), nullable=False),
        sa.Column("objective_key", sa.String(length=120), nullable=False),
        sa.Column("reflection", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["enrollment_id"], ["practicum_enrollments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("enrollment_id", "objective_key", name="uq_practicum_progress_enrollment_objective"),
    )
    op.create_index(
        op.f("ix_practicum_objective_progress_enrollment_id"),
        "practicum_objective_progress",
        ["enrollment_id"],
        unique=False,
    )

    op.create_table(
        "practicum_evidence_references",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("objective_progress_id", sa.Integer(), nullable=False),
        sa.Column("research_evidence_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["objective_progress_id"], ["practicum_objective_progress.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["research_evidence_id"], ["research_evidence.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "objective_progress_id", "research_evidence_id", name="uq_practicum_reference_progress_evidence"
        ),
    )
    op.create_index(
        op.f("ix_practicum_evidence_references_objective_progress_id"),
        "practicum_evidence_references",
        ["objective_progress_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_practicum_evidence_references_research_evidence_id"),
        "practicum_evidence_references",
        ["research_evidence_id"],
        unique=False,
    )

    op.create_table(
        "practicum_review_decisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("enrollment_id", sa.Integer(), nullable=False),
        sa.Column("reviewer_user_id", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["enrollment_id"], ["practicum_enrollments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("enrollment_id", "reviewer_user_id", "created_at"):
        op.create_index(
            op.f(f"ix_practicum_review_decisions_{column}"),
            "practicum_review_decisions",
            [column],
            unique=False,
        )


def downgrade() -> None:
    for column in ("created_at", "reviewer_user_id", "enrollment_id"):
        op.drop_index(op.f(f"ix_practicum_review_decisions_{column}"), table_name="practicum_review_decisions")
    op.drop_table("practicum_review_decisions")

    op.drop_index(
        op.f("ix_practicum_evidence_references_research_evidence_id"),
        table_name="practicum_evidence_references",
    )
    op.drop_index(
        op.f("ix_practicum_evidence_references_objective_progress_id"),
        table_name="practicum_evidence_references",
    )
    op.drop_table("practicum_evidence_references")

    op.drop_index(
        op.f("ix_practicum_objective_progress_enrollment_id"), table_name="practicum_objective_progress"
    )
    op.drop_table("practicum_objective_progress")

    for column in ("status", "research_project_id", "template_id", "user_id"):
        op.drop_index(op.f(f"ix_practicum_enrollments_{column}"), table_name="practicum_enrollments")
    op.drop_table("practicum_enrollments")

    op.drop_index(op.f("ix_practicum_objectives_competency"), table_name="practicum_objectives")
    op.drop_index(op.f("ix_practicum_objectives_template_id"), table_name="practicum_objectives")
    op.drop_table("practicum_objectives")

    op.drop_index(op.f("ix_practicum_templates_status"), table_name="practicum_templates")
    op.drop_index(op.f("ix_practicum_templates_slug"), table_name="practicum_templates")
    op.drop_table("practicum_templates")
