"""add remediation progress history

Revision ID: 0034_remediation_progress_history
Revises: 0033_remediation_progress
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0034_remediation_progress_history"
down_revision: str | None = "0033_remediation_progress"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "remediation_progress_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("progress_id", sa.Integer(), nullable=False),
        sa.Column("investigation_id", sa.Integer(), nullable=False),
        sa.Column("claim_id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("action_type_snapshot", sa.String(length=48), nullable=False),
        sa.Column("priority_snapshot", sa.Integer(), nullable=False),
        sa.Column("plan_generated_at_snapshot", sa.DateTime(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["progress_id"], ["remediation_progress.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["investigation_id"], ["investigations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["claim_id"], ["investigation_claims.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("id", "progress_id", "investigation_id", "claim_id", "owner_id", "status", "recorded_at"):
        op.create_index(
            op.f(f"ix_remediation_progress_history_{column}"),
            "remediation_progress_history",
            [column],
            unique=False,
        )


def downgrade() -> None:
    for column in ("recorded_at", "status", "owner_id", "claim_id", "investigation_id", "progress_id", "id"):
        op.drop_index(
            op.f(f"ix_remediation_progress_history_{column}"),
            table_name="remediation_progress_history",
        )
    op.drop_table("remediation_progress_history")
