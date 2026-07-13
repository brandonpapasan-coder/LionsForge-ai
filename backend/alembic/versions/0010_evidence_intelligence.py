"""add evidence intelligence records

Revision ID: 0010_evidence_intelligence
Revises: 0009_entity_resolution
Create Date: 2026-07-13 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_evidence_intelligence"
down_revision: str | None = "0009_entity_resolution"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evidence_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("source_title", sa.String(length=300), nullable=False),
        sa.Column("publisher", sa.String(length=200), nullable=True),
        sa.Column("author", sa.String(length=200), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("stance", sa.String(length=16), nullable=False),
        sa.Column("contradiction_key", sa.String(length=160), nullable=True),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("credibility_score", sa.Float(), nullable=False),
        sa.Column("freshness_score", sa.Float(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("validation_status", sa.String(length=24), nullable=False),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["entity_id"], ["knowledge_entities.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["research_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "fingerprint", name="uq_evidence_owner_fingerprint"),
    )
    for column in (
        "id",
        "owner_id",
        "project_id",
        "entity_id",
        "source_type",
        "stance",
        "contradiction_key",
        "fingerprint",
        "validation_status",
    ):
        op.create_index(f"ix_evidence_records_{column}", "evidence_records", [column])


def downgrade() -> None:
    for column in reversed(
        (
            "id",
            "owner_id",
            "project_id",
            "entity_id",
            "source_type",
            "stance",
            "contradiction_key",
            "fingerprint",
            "validation_status",
        )
    ):
        op.drop_index(f"ix_evidence_records_{column}", table_name="evidence_records")
    op.drop_table("evidence_records")
