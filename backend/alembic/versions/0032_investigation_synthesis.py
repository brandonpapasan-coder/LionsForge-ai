"""add investigation synthesis

Revision ID: 0032_investigation_synthesis
Revises: 0031_claim_validation_ledger
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0032_investigation_synthesis"
down_revision: str | None = "0031_claim_validation_ledger"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "investigation_syntheses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("investigation_id", sa.Integer(), nullable=False),
        sa.Column("findings", sa.Text(), nullable=True),
        sa.Column("limitations", sa.Text(), nullable=True),
        sa.Column("unresolved_questions", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("investigation_id", name="uq_investigation_syntheses_investigation_id"),
    )
    op.create_index(
        op.f("ix_investigation_syntheses_id"),
        "investigation_syntheses",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_investigation_syntheses_investigation_id"),
        "investigation_syntheses",
        ["investigation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_investigation_syntheses_investigation_id"), table_name="investigation_syntheses")
    op.drop_index(op.f("ix_investigation_syntheses_id"), table_name="investigation_syntheses")
    op.drop_table("investigation_syntheses")
