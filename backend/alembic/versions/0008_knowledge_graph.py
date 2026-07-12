"""add knowledge graph entities and relationships

Revision ID: 0008_knowledge_graph
Revises: 0007_education_progress
Create Date: 2026-07-12 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_knowledge_graph"
down_revision: str | None = "0007_education_progress"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_entities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("validation_status", sa.String(length=24), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "entity_type", "name", name="uq_knowledge_entity_owner_type_name"),
    )
    op.create_index("ix_knowledge_entities_id", "knowledge_entities", ["id"], unique=False)
    op.create_index("ix_knowledge_entities_owner_id", "knowledge_entities", ["owner_id"], unique=False)
    op.create_index("ix_knowledge_entities_entity_type", "knowledge_entities", ["entity_type"], unique=False)
    op.create_index("ix_knowledge_entities_name", "knowledge_entities", ["name"], unique=False)
    op.create_index("ix_knowledge_entities_validation_status", "knowledge_entities", ["validation_status"], unique=False)

    op.create_table(
        "knowledge_relationships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("source_entity_id", sa.Integer(), nullable=False),
        sa.Column("target_entity_id", sa.Integer(), nullable=False),
        sa.Column("relationship_type", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("validation_status", sa.String(length=24), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_entity_id"], ["knowledge_entities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_entity_id"], ["knowledge_entities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "owner_id",
            "source_entity_id",
            "target_entity_id",
            "relationship_type",
            name="uq_knowledge_relationship_owner_path_type",
        ),
    )
    op.create_index("ix_knowledge_relationships_id", "knowledge_relationships", ["id"], unique=False)
    op.create_index("ix_knowledge_relationships_owner_id", "knowledge_relationships", ["owner_id"], unique=False)
    op.create_index("ix_knowledge_relationships_source_entity_id", "knowledge_relationships", ["source_entity_id"], unique=False)
    op.create_index("ix_knowledge_relationships_target_entity_id", "knowledge_relationships", ["target_entity_id"], unique=False)
    op.create_index("ix_knowledge_relationships_relationship_type", "knowledge_relationships", ["relationship_type"], unique=False)
    op.create_index("ix_knowledge_relationships_validation_status", "knowledge_relationships", ["validation_status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_knowledge_relationships_validation_status", table_name="knowledge_relationships")
    op.drop_index("ix_knowledge_relationships_relationship_type", table_name="knowledge_relationships")
    op.drop_index("ix_knowledge_relationships_target_entity_id", table_name="knowledge_relationships")
    op.drop_index("ix_knowledge_relationships_source_entity_id", table_name="knowledge_relationships")
    op.drop_index("ix_knowledge_relationships_owner_id", table_name="knowledge_relationships")
    op.drop_index("ix_knowledge_relationships_id", table_name="knowledge_relationships")
    op.drop_table("knowledge_relationships")

    op.drop_index("ix_knowledge_entities_validation_status", table_name="knowledge_entities")
    op.drop_index("ix_knowledge_entities_name", table_name="knowledge_entities")
    op.drop_index("ix_knowledge_entities_entity_type", table_name="knowledge_entities")
    op.drop_index("ix_knowledge_entities_owner_id", table_name="knowledge_entities")
    op.drop_index("ix_knowledge_entities_id", table_name="knowledge_entities")
    op.drop_table("knowledge_entities")
