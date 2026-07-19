"""add investigation synthesis fields

Revision ID: 0031_investigation_synthesis
Revises: 0030_evidence_assessment
Create Date: 2026-07-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0031_investigation_synthesis"
down_revision = "0030_evidence_assessment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("investigations", sa.Column("findings", sa.Text(), nullable=True))
    op.add_column("investigations", sa.Column("limitations", sa.Text(), nullable=True))
    op.add_column("investigations", sa.Column("unresolved_questions", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("investigations", "unresolved_questions")
    op.drop_column("investigations", "limitations")
    op.drop_column("investigations", "findings")
