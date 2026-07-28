"""add payment provider validation records

Revision ID: 0039_provider_validation
Revises: 0038_promotion_rollout
"""

from alembic import op
import sqlalchemy as sa

revision = "0039_provider_validation"
down_revision = "0038_promotion_rollout"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_provider_validations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("configuration_digest", sa.String(length=64), nullable=False),
        sa.Column("validation_status", sa.String(length=24), nullable=False),
        sa.Column("reason_code", sa.String(length=80), nullable=False),
        sa.Column("validated_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("api_reference_present", sa.Boolean(), nullable=False),
        sa.Column("webhook_reference_present", sa.Boolean(), nullable=False),
        sa.Column("price_references_present", sa.Boolean(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
    )
    for column in ("provider", "mode", "configuration_digest", "validation_status", "validated_at", "expires_at"):
        op.create_index(f"ix_payment_provider_validations_{column}", "payment_provider_validations", [column])


def downgrade() -> None:
    op.drop_table("payment_provider_validations")
