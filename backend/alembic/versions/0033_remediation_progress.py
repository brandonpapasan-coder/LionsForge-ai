"""add remediation progress ledger

Revision ID: 0033_remediation_progress
Revises: 0032_investigation_synthesis
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0033_remediation_progress"
down_revision: str | None = "0032_investigation_synthesis"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "remediation_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("investigation_id", sa.Integer(), nullable=False),
        sa.Column("claim_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("action_type_snapshot", sa.String(length=48), nullable=False),
        sa.Column("priority_snapshot", sa.Integer(), nullable=False),
        sa.Column("plan_generated_at_snapshot", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["investigation_claims.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "investigation_id",
            "claim_id",
            "owner_id",
            name="uq_remediation_progress_investigation_claim_owner",
        ),
    )
    op.create_index(op.f("ix_remediation_progress_id"), "remediation_progress", ["id"], unique=False)
    op.create_index(
        op.f("ix_remediation_progress_investigation_id"),
        "remediation_progress",
        ["investigation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_remediation_progress_claim_id"),
        "remediation_progress",
        ["claim_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_remediation_progress_owner_id"),
        "remediation_progress",
        ["owner_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_remediation_progress_status"),
        "remediation_progress",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_remediation_progress_status"), table_name="remediation_progress")
    op.drop_index(op.f("ix_remediation_progress_owner_id"), table_name="remediation_progress")
    op.drop_index(op.f("ix_remediation_progress_claim_id"), table_name="remediation_progress")
    op.drop_index(op.f("ix_remediation_progress_investigation_id"), table_name="remediation_progress")
    op.drop_index(op.f("ix_remediation_progress_id"), table_name="remediation_progress")
    op.drop_table("remediation_progress")
