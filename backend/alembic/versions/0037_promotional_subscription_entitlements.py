"""add promotional subscription entitlements

Revision ID: 0037_promotion_entitlements
Revises: 0036_roadmap_action_ledger

The revision identifier is intentionally kept within Alembic's default
32-character version column limit used by PostgreSQL validation.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0037_promotion_entitlements"
down_revision: str | None = "0036_roadmap_action_ledger"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "promotion_campaigns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("promotion_type", sa.String(length=32), nullable=False),
        sa.Column("discount_percent", sa.Integer(), nullable=False),
        sa.Column("duration_months", sa.Integer(), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("discount_percent > 0 AND discount_percent <= 100", name="ck_promotion_campaign_discount"),
        sa.CheckConstraint("capacity IS NULL OR capacity > 0", name="ck_promotion_campaign_capacity"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_promotion_campaign_slug"),
    )
    op.create_index(op.f("ix_promotion_campaigns_promotion_type"), "promotion_campaigns", ["promotion_type"], unique=False)

    op.create_table(
        "promotion_eligibilities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("verified_account_id", sa.String(length=120), nullable=False),
        sa.Column("reserved_until", sa.DateTime(), nullable=True),
        sa.Column("eligibility_reason", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["promotion_campaigns.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_id", "user_id", name="uq_promotion_eligibility_campaign_user"),
    )
    for column in ("campaign_id", "user_id", "status", "verified_account_id", "reserved_until"):
        op.create_index(op.f(f"ix_promotion_eligibilities_{column}"), "promotion_eligibilities", [column], unique=False)

    op.create_table(
        "founding_subscriber_sequences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("eligibility_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("allocation_status", sa.String(length=24), nullable=False),
        sa.Column("reserved_at", sa.DateTime(), nullable=False),
        sa.Column("released_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("position > 0 AND position <= 20000", name="ck_founding_sequence_position"),
        sa.ForeignKeyConstraint(["campaign_id"], ["promotion_campaigns.id"]),
        sa.ForeignKeyConstraint(["eligibility_id"], ["promotion_eligibilities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_id", "eligibility_id", name="uq_founding_sequence_campaign_eligibility"),
        sa.UniqueConstraint("campaign_id", "position", name="uq_founding_sequence_campaign_position"),
    )
    for column in ("campaign_id", "allocation_status"):
        op.create_index(op.f(f"ix_founding_subscriber_sequences_{column}"), "founding_subscriber_sequences", [column], unique=False)

    op.create_table(
        "promotion_redemptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("eligibility_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_customer_id", sa.String(length=160), nullable=False),
        sa.Column("provider_subscription_id", sa.String(length=160), nullable=False),
        sa.Column("provider_discount_id", sa.String(length=160), nullable=True),
        sa.Column("internal_entitlement_id", sa.String(length=120), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["eligibility_id"], ["promotion_eligibilities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("eligibility_id", name="uq_promotion_redemption_eligibility"),
        sa.UniqueConstraint("provider", "provider_subscription_id", name="uq_promotion_redemption_provider_subscription"),
    )
    for column in ("eligibility_id", "provider_customer_id", "internal_entitlement_id", "status"):
        op.create_index(op.f(f"ix_promotion_redemptions_{column}"), "promotion_redemptions", [column], unique=False)

    op.create_table(
        "subscription_price_protections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("redemption_id", sa.Integer(), nullable=False),
        sa.Column("protection_type", sa.String(length=32), nullable=False),
        sa.Column("protected_percent", sa.Integer(), nullable=False),
        sa.Column("protected_until", sa.DateTime(), nullable=True),
        sa.Column("continuous_subscription_required", sa.Boolean(), nullable=False),
        sa.Column("grace_period_days", sa.Integer(), nullable=False),
        sa.Column("regular_price_amount_cents", sa.Integer(), nullable=False),
        sa.Column("regular_price_currency", sa.String(length=3), nullable=False),
        sa.Column("regular_price_effective_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["redemption_id"], ["promotion_redemptions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("redemption_id", name="uq_subscription_price_protection_redemption"),
    )
    op.create_index(op.f("ix_subscription_price_protections_status"), "subscription_price_protections", ["status"], unique=False)

    op.create_table(
        "promotion_audit_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=True),
        sa.Column("eligibility_id", sa.Integer(), nullable=True),
        sa.Column("redemption_id", sa.Integer(), nullable=True),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_reference", sa.String(length=120), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("reason_code", sa.String(length=80), nullable=False),
        sa.Column("event_payload", sa.JSON(), nullable=False),
        sa.Column("previous_record_sha256", sa.String(length=64), nullable=True),
        sa.Column("record_sha256", sa.String(length=64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["promotion_campaigns.id"]),
        sa.ForeignKeyConstraint(["eligibility_id"], ["promotion_eligibilities.id"]),
        sa.ForeignKeyConstraint(["redemption_id"], ["promotion_redemptions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("record_sha256"),
    )
    for column in ("campaign_id", "eligibility_id", "redemption_id", "event_type", "occurred_at"):
        op.create_index(op.f(f"ix_promotion_audit_records_{column}"), "promotion_audit_records", [column], unique=False)


def downgrade() -> None:
    for column in ("occurred_at", "event_type", "redemption_id", "eligibility_id", "campaign_id"):
        op.drop_index(op.f(f"ix_promotion_audit_records_{column}"), table_name="promotion_audit_records")
    op.drop_table("promotion_audit_records")
    op.drop_index(op.f("ix_subscription_price_protections_status"), table_name="subscription_price_protections")
    op.drop_table("subscription_price_protections")
    for column in ("status", "internal_entitlement_id", "provider_customer_id", "eligibility_id"):
        op.drop_index(op.f(f"ix_promotion_redemptions_{column}"), table_name="promotion_redemptions")
    op.drop_table("promotion_redemptions")
    for column in ("allocation_status", "campaign_id"):
        op.drop_index(op.f(f"ix_founding_subscriber_sequences_{column}"), table_name="founding_subscriber_sequences")
    op.drop_table("founding_subscriber_sequences")
    for column in ("reserved_until", "verified_account_id", "status", "user_id", "campaign_id"):
        op.drop_index(op.f(f"ix_promotion_eligibilities_{column}"), table_name="promotion_eligibilities")
    op.drop_table("promotion_eligibilities")
    op.drop_index(op.f("ix_promotion_campaigns_promotion_type"), table_name="promotion_campaigns")
    op.drop_table("promotion_campaigns")
