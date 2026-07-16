"""add market learning evidence links

Revision ID: 0020_market_learning_evidence
Revises: 0019_market_learning_sessions
Create Date: 2026-07-16 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_market_learning_evidence"
down_revision: str | None = "0019_market_learning_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_learning_evidence_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("evidence_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["market_learning_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence_records.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["research_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_market_learning_evidence_session"),
        sa.UniqueConstraint("evidence_id", name="uq_market_learning_evidence_record"),
    )
    op.create_index("ix_market_learning_evidence_links_id", "market_learning_evidence_links", ["id"])
    op.create_index("ix_market_learning_evidence_links_owner_id", "market_learning_evidence_links", ["owner_id"])
    op.create_index("ix_market_learning_evidence_links_session_id", "market_learning_evidence_links", ["session_id"])
    op.create_index("ix_market_learning_evidence_links_evidence_id", "market_learning_evidence_links", ["evidence_id"])
    op.create_index("ix_market_learning_evidence_links_project_id", "market_learning_evidence_links", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_market_learning_evidence_links_project_id", table_name="market_learning_evidence_links")
    op.drop_index("ix_market_learning_evidence_links_evidence_id", table_name="market_learning_evidence_links")
    op.drop_index("ix_market_learning_evidence_links_session_id", table_name="market_learning_evidence_links")
    op.drop_index("ix_market_learning_evidence_links_owner_id", table_name="market_learning_evidence_links")
    op.drop_index("ix_market_learning_evidence_links_id", table_name="market_learning_evidence_links")
    op.drop_table("market_learning_evidence_links")
