"""add market simulator tables

Revision ID: 0018_market_simulator
Revises: 0017_evidence_review_audit
Create Date: 2026-07-15 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_market_simulator"
down_revision: str | None = "0017_evidence_review_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "simulation_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("starting_cash", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("cash_balance", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_simulation_accounts_id", "simulation_accounts", ["id"])
    op.create_index("ix_simulation_accounts_owner_id", "simulation_accounts", ["owner_id"])
    op.create_index("ix_simulation_accounts_status", "simulation_accounts", ["status"])

    op.create_table(
        "virtual_positions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=24), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("average_price", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("last_price", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["simulation_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "symbol", name="uq_virtual_position_account_symbol"),
    )
    op.create_index("ix_virtual_positions_id", "virtual_positions", ["id"])
    op.create_index("ix_virtual_positions_account_id", "virtual_positions", ["account_id"])
    op.create_index("ix_virtual_positions_symbol", "virtual_positions", ["symbol"])

    op.create_table(
        "simulated_trades",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=24), nullable=False),
        sa.Column("side", sa.String(length=8), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("execution_price", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("notional", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("executed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["simulation_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_simulated_trades_id", "simulated_trades", ["id"])
    op.create_index("ix_simulated_trades_account_id", "simulated_trades", ["account_id"])
    op.create_index("ix_simulated_trades_symbol", "simulated_trades", ["symbol"])


def downgrade() -> None:
    op.drop_index("ix_simulated_trades_symbol", table_name="simulated_trades")
    op.drop_index("ix_simulated_trades_account_id", table_name="simulated_trades")
    op.drop_index("ix_simulated_trades_id", table_name="simulated_trades")
    op.drop_table("simulated_trades")

    op.drop_index("ix_virtual_positions_symbol", table_name="virtual_positions")
    op.drop_index("ix_virtual_positions_account_id", table_name="virtual_positions")
    op.drop_index("ix_virtual_positions_id", table_name="virtual_positions")
    op.drop_table("virtual_positions")

    op.drop_index("ix_simulation_accounts_status", table_name="simulation_accounts")
    op.drop_index("ix_simulation_accounts_owner_id", table_name="simulation_accounts")
    op.drop_index("ix_simulation_accounts_id", table_name="simulation_accounts")
    op.drop_table("simulation_accounts")
