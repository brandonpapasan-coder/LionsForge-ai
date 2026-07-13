"""add executive brief snapshots

Revision ID: 0011_executive_brief_snapshots
Revises: 0010_evidence_intelligence
Create Date: 2026-07-13 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_executive_brief_snapshots"
down_revision: str | None = "0010_evidence_intelligence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "executive_brief_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("recommendation", sa.String(length=32), nullable=False),
        sa.Column("decision_readiness_score", sa.Float(), nullable=False),
        sa.Column("research_trust_index", sa.Float(), nullable=False),
        sa.Column("consensus_status", sa.String(length=32), nullable=False),
        sa.Column("overall_confidence", sa.Float(), nullable=False),
        sa.Column("methodology_version", sa.String(length=64), nullable=False),
        sa.Column("source_evidence_ids", sa.JSON(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["research_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "project_id", "fingerprint", name="uq_executive_snapshot_state"),
    )
    for column in ("id", "owner_id", "project_id", "fingerprint", "recommendation", "created_at"):
        op.create_index(f"ix_executive_brief_snapshots_{column}", "executive_brief_snapshots", [column])


def downgrade() -> None:
    for column in reversed(("id", "owner_id", "project_id", "fingerprint", "recommendation", "created_at")):
        op.drop_index(f"ix_executive_brief_snapshots_{column}", table_name="executive_brief_snapshots")
    op.drop_table("executive_brief_snapshots")
