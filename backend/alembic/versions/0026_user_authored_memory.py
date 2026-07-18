"""allow user-authored knowledge memories

Revision ID: 0026_user_authored_memory
Revises: 0025_conclusion_defense
Create Date: 2026-07-18 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026_user_authored_memory"
down_revision: str | None = "0025_conclusion_defense"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "knowledge_memories",
        "mission_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.alter_column(
        "knowledge_memories",
        "snapshot_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    op.execute("DELETE FROM knowledge_memories WHERE mission_id IS NULL OR snapshot_id IS NULL")
    op.alter_column(
        "knowledge_memories",
        "snapshot_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "knowledge_memories",
        "mission_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
