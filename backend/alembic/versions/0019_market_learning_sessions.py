"""add market learning sessions

Revision ID: 0019_market_learning_sessions
Revises: 0018_market_simulator
Create Date: 2026-07-15 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019_market_learning_sessions"
down_revision: str | None = "0018_market_simulator"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_learning_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("scenario_name", sa.String(length=32), nullable=False),
        sa.Column("steps", sa.Integer(), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("risk_tier", sa.String(length=16), nullable=False),
        sa.Column("projected_return", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("learner_reflection", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["simulation_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_market_learning_sessions_id", "market_learning_sessions", ["id"])
    op.create_index("ix_market_learning_sessions_account_id", "market_learning_sessions", ["account_id"])
    op.create_index("ix_market_learning_sessions_scenario_name", "market_learning_sessions", ["scenario_name"])
    op.create_index("ix_market_learning_sessions_risk_tier", "market_learning_sessions", ["risk_tier"])
    op.create_index("ix_market_learning_sessions_status", "market_learning_sessions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_market_learning_sessions_status", table_name="market_learning_sessions")
    op.drop_index("ix_market_learning_sessions_risk_tier", table_name="market_learning_sessions")
    op.drop_index("ix_market_learning_sessions_scenario_name", table_name="market_learning_sessions")
    op.drop_index("ix_market_learning_sessions_account_id", table_name="market_learning_sessions")
    op.drop_index("ix_market_learning_sessions_id", table_name="market_learning_sessions")
    op.drop_table("market_learning_sessions")
