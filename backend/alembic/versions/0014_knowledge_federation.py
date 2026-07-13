"""add cross-project knowledge federation

Revision ID: 0014_knowledge_federation
Revises: 0013_knowledge_memory
Create Date: 2026-07-13 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_knowledge_federation"
down_revision: str | None = "0013_knowledge_memory"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_federation_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("source_memory_id", sa.Integer(), nullable=False),
        sa.Column("target_memory_id", sa.Integer(), nullable=False),
        sa.Column("source_project_id", sa.Integer(), nullable=False),
        sa.Column("target_project_id", sa.Integer(), nullable=False),
        sa.Column("link_type", sa.String(length=24), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("score_components", sa.JSON(), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_memory_id"], ["knowledge_memories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_memory_id"], ["knowledge_memories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_project_id"], ["research_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_project_id"], ["research_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "fingerprint", name="uq_knowledge_federation_link"),
    )
    for column in ("id", "owner_id", "source_memory_id", "target_memory_id", "source_project_id", "target_project_id", "link_type", "status", "fingerprint"):
        op.create_index(f"ix_knowledge_federation_links_{column}", "knowledge_federation_links", [column])

    op.create_table(
        "knowledge_federation_revisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("link_id", sa.Integer(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("link_type", sa.String(length=24), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("score_components", sa.JSON(), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["link_id"], ["knowledge_federation_links.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("link_id", "revision_number", name="uq_knowledge_federation_revision"),
    )
    op.create_index("ix_knowledge_federation_revisions_id", "knowledge_federation_revisions", ["id"])
    op.create_index("ix_knowledge_federation_revisions_link_id", "knowledge_federation_revisions", ["link_id"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_federation_revisions_link_id", table_name="knowledge_federation_revisions")
    op.drop_index("ix_knowledge_federation_revisions_id", table_name="knowledge_federation_revisions")
    op.drop_table("knowledge_federation_revisions")
    for column in reversed(("id", "owner_id", "source_memory_id", "target_memory_id", "source_project_id", "target_project_id", "link_type", "status", "fingerprint")):
        op.drop_index(f"ix_knowledge_federation_links_{column}", table_name="knowledge_federation_links")
    op.drop_table("knowledge_federation_links")
