"""add persistent knowledge memory

Revision ID: 0013_knowledge_memory
Revises: 0012_mission_runtime
Create Date: 2026-07-13 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_knowledge_memory"
down_revision: str | None = "0012_mission_runtime"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_memories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("mission_id", sa.Integer(), nullable=False),
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("source_evidence_ids", sa.JSON(), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("superseded_by_id", sa.Integer(), nullable=True),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["mission_id"], ["missions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["research_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["executive_brief_snapshots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["superseded_by_id"], ["knowledge_memories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "project_id", "fingerprint", name="uq_knowledge_memory_state"),
    )
    for column in ("id", "owner_id", "project_id", "mission_id", "snapshot_id", "fingerprint", "category", "status"):
        op.create_index(f"ix_knowledge_memories_{column}", "knowledge_memories", [column])

    op.create_table(
        "knowledge_memory_revisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("memory_id", sa.Integer(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("source_evidence_ids", sa.JSON(), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["memory_id"], ["knowledge_memories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("memory_id", "revision_number", name="uq_knowledge_memory_revision"),
    )
    op.create_index("ix_knowledge_memory_revisions_id", "knowledge_memory_revisions", ["id"])
    op.create_index("ix_knowledge_memory_revisions_memory_id", "knowledge_memory_revisions", ["memory_id"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_memory_revisions_memory_id", table_name="knowledge_memory_revisions")
    op.drop_index("ix_knowledge_memory_revisions_id", table_name="knowledge_memory_revisions")
    op.drop_table("knowledge_memory_revisions")
    for column in reversed(("id", "owner_id", "project_id", "mission_id", "snapshot_id", "fingerprint", "category", "status")):
        op.drop_index(f"ix_knowledge_memories_{column}", table_name="knowledge_memories")
    op.drop_table("knowledge_memories")
