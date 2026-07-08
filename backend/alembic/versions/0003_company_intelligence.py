"""add company intelligence table

Revision ID: 0003_company_intelligence
Revises: 0002_core_product_tables
Create Date: 2026-07-08 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_company_intelligence"
down_revision: str | None = "0002_core_product_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("exchange", sa.String(length=64), nullable=True),
        sa.Column("sector", sa.String(length=128), nullable=True),
        sa.Column("industry", sa.String(length=128), nullable=True),
        sa.Column("country", sa.String(length=64), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_companies_id", "companies", ["id"])
    op.create_index("ix_companies_name", "companies", ["name"])
    op.create_index("ix_companies_ticker", "companies", ["ticker"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_companies_ticker", table_name="companies")
    op.drop_index("ix_companies_name", table_name="companies")
    op.drop_index("ix_companies_id", table_name="companies")
    op.drop_table("companies")
