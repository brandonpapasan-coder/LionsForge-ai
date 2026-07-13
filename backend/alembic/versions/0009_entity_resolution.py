"""add entity aliases and merge audits

Revision ID: 0009_entity_resolution
Revises: 0008_knowledge_graph
Create Date: 2026-07-12 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_entity_resolution"
down_revision: str | None = "0008_knowledge_graph"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_entity_aliases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(length=200), nullable=False),
        sa.Column("normalized_alias", sa.String(length=200), nullable=False),
        sa.Column("alias_type", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["entity_id"], ["knowledge_entities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "normalized_alias", name="uq_entity_alias_owner_normalized"),
    )
    op.create_index("ix_knowledge_entity_aliases_id", "knowledge_entity_aliases", ["id"])
    op.create_index("ix_knowledge_entity_aliases_owner_id", "knowledge_entity_aliases", ["owner_id"])
    op.create_index("ix_knowledge_entity_aliases_entity_id", "knowledge_entity_aliases", ["entity_id"])
    op.create_index("ix_knowledge_entity_aliases_normalized_alias", "knowledge_entity_aliases", ["normalized_alias"])

    op.create_table(
        "knowledge_entity_merge_audits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("canonical_entity_id", sa.Integer(), nullable=False),
        sa.Column("merged_entity_snapshot", sa.JSON(), nullable=False),
        sa.Column("moved_relationship_ids", sa.JSON(), nullable=False),
        sa.Column("created_alias_ids", sa.JSON(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["canonical_entity_id"], ["knowledge_entities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_entity_merge_audits_id", "knowledge_entity_merge_audits", ["id"])
    op.create_index("ix_knowledge_entity_merge_audits_owner_id", "knowledge_entity_merge_audits", ["owner_id"])
    op.create_index("ix_knowledge_entity_merge_audits_canonical_entity_id", "knowledge_entity_merge_audits", ["canonical_entity_id"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_entity_merge_audits_canonical_entity_id", table_name="knowledge_entity_merge_audits")
    op.drop_index("ix_knowledge_entity_merge_audits_owner_id", table_name="knowledge_entity_merge_audits")
    op.drop_index("ix_knowledge_entity_merge_audits_id", table_name="knowledge_entity_merge_audits")
    op.drop_table("knowledge_entity_merge_audits")
    op.drop_index("ix_knowledge_entity_aliases_normalized_alias", table_name="knowledge_entity_aliases")
    op.drop_index("ix_knowledge_entity_aliases_entity_id", table_name="knowledge_entity_aliases")
    op.drop_index("ix_knowledge_entity_aliases_owner_id", table_name="knowledge_entity_aliases")
    op.drop_index("ix_knowledge_entity_aliases_id", table_name="knowledge_entity_aliases")
    op.drop_table("knowledge_entity_aliases")
