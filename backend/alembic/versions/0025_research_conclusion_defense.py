"""add research conclusion defense review

Revision ID: 0025_conclusion_defense
Revises: 0024_research_conclusion
Create Date: 2026-07-16 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0025_conclusion_defense"
down_revision: str | None = "0024_research_conclusion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "research_conclusion_defenses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("conclusion_revision_number", sa.Integer(), nullable=True),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.Column("evidence_coverage", sa.Text(), nullable=False),
        sa.Column("strongest_counterargument", sa.Text(), nullable=False),
        sa.Column("known_limitations", sa.Text(), nullable=False),
        sa.Column("unresolved_questions", sa.Text(), nullable=False),
        sa.Column("confidence_rationale", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("missing_sections", sa.JSON(), nullable=False),
        sa.Column("revision_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["research_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "project_id", name="uq_research_conclusion_defense_owner_project"),
    )
    for column in ("id", "owner_id", "project_id", "status"):
        op.create_index(f"ix_research_conclusion_defenses_{column}", "research_conclusion_defenses", [column])

    op.create_table(
        "research_conclusion_defense_revisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("defense_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("conclusion_revision_number", sa.Integer(), nullable=True),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.Column("evidence_coverage", sa.Text(), nullable=False),
        sa.Column("strongest_counterargument", sa.Text(), nullable=False),
        sa.Column("known_limitations", sa.Text(), nullable=False),
        sa.Column("unresolved_questions", sa.Text(), nullable=False),
        sa.Column("confidence_rationale", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("missing_sections", sa.JSON(), nullable=False),
        sa.Column("revision_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["defense_id"], ["research_conclusion_defenses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["research_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("defense_id", "revision_number", name="uq_research_conclusion_defense_revision_number"),
    )
    for column in ("id", "defense_id", "owner_id", "project_id", "status"):
        op.create_index(f"ix_research_conclusion_defense_revisions_{column}", "research_conclusion_defense_revisions", [column])


def downgrade() -> None:
    for column in ("status", "project_id", "owner_id", "defense_id", "id"):
        op.drop_index(f"ix_research_conclusion_defense_revisions_{column}", table_name="research_conclusion_defense_revisions")
    op.drop_table("research_conclusion_defense_revisions")
    for column in ("status", "project_id", "owner_id", "id"):
        op.drop_index(f"ix_research_conclusion_defenses_{column}", table_name="research_conclusion_defenses")
    op.drop_table("research_conclusion_defenses")
