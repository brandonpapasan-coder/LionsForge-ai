"""add mission runtime

Revision ID: 0012_mission_runtime
Revises: 0011_executive_brief_snapshots
Create Date: 2026-07-13 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_mission_runtime"
down_revision: str | None = "0011_executive_brief_snapshots"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "missions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("success_criteria", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("current_step_order", sa.Integer(), nullable=False),
        sa.Column("final_snapshot_id", sa.Integer(), nullable=True),
        sa.Column("blocking_reason", sa.Text(), nullable=True),
        sa.Column("methodology_version", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["final_snapshot_id"], ["executive_brief_snapshots.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["research_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("id", "owner_id", "project_id", "status"):
        op.create_index(f"ix_missions_{column}", "missions", [column])

    op.create_table(
        "mission_steps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mission_id", sa.Integer(), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("inputs", sa.JSON(), nullable=False),
        sa.Column("outputs", sa.JSON(), nullable=False),
        sa.Column("blocking_reason", sa.Text(), nullable=True),
        sa.Column("methodology_version", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["mission_id"], ["missions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mission_id", "step_order", "attempt", name="uq_mission_step_attempt"),
    )
    for column in ("id", "mission_id", "step_order", "status"):
        op.create_index(f"ix_mission_steps_{column}", "mission_steps", [column])


def downgrade() -> None:
    for column in reversed(("id", "mission_id", "step_order", "status")):
        op.drop_index(f"ix_mission_steps_{column}", table_name="mission_steps")
    op.drop_table("mission_steps")
    for column in reversed(("id", "owner_id", "project_id", "status")):
        op.drop_index(f"ix_missions_{column}", table_name="missions")
    op.drop_table("missions")
