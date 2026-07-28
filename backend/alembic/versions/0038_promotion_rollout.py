"""add promotion rollout persistence

Revision ID: 0038_promotion_rollout
Revises: 0037_promotion_entitlements
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0038_promotion_rollout"
down_revision: str | None = "0037_promotion_entitlements"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "promotion_rollout_authorizations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rollout_state", sa.String(length=24), nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_reference", sa.String(length=120), nullable=False),
        sa.Column("reason_code", sa.String(length=80), nullable=False),
        sa.Column("configuration_digest", sa.String(length=64), nullable=False),
        sa.Column("authorized_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("rollout_state", "configuration_digest", "authorized_at"):
        op.create_index(op.f(f"ix_promotion_rollout_authorizations_{column}"), "promotion_rollout_authorizations", [column], unique=False)

    op.create_table(
        "promotion_checkout_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("eligibility_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("request_digest", sa.String(length=64), nullable=False),
        sa.Column("provider_session_id", sa.String(length=160), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["eligibility_id"], ["promotion_eligibilities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "idempotency_key", name="uq_promotion_checkout_provider_key"),
    )
    for column in ("eligibility_id", "provider_session_id", "status"):
        op.create_index(op.f(f"ix_promotion_checkout_requests_{column}"), "promotion_checkout_requests", [column], unique=False)

    op.create_table(
        "promotion_provider_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_event_id", sa.String(length=160), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("payload_digest", sa.String(length=64), nullable=False),
        sa.Column("signature_verified", sa.Boolean(), nullable=False),
        sa.Column("processing_status", sa.String(length=32), nullable=False),
        sa.Column("processing_result", sa.JSON(), nullable=False),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_event_id", name="uq_promotion_provider_event"),
    )
    for column in ("event_type", "processing_status", "received_at"):
        op.create_index(op.f(f"ix_promotion_provider_events_{column}"), "promotion_provider_events", [column], unique=False)


def downgrade() -> None:
    for column in ("received_at", "processing_status", "event_type"):
        op.drop_index(op.f(f"ix_promotion_provider_events_{column}"), table_name="promotion_provider_events")
    op.drop_table("promotion_provider_events")
    for column in ("status", "provider_session_id", "eligibility_id"):
        op.drop_index(op.f(f"ix_promotion_checkout_requests_{column}"), table_name="promotion_checkout_requests")
    op.drop_table("promotion_checkout_requests")
    for column in ("authorized_at", "configuration_digest", "rollout_state"):
        op.drop_index(op.f(f"ix_promotion_rollout_authorizations_{column}"), table_name="promotion_rollout_authorizations")
    op.drop_table("promotion_rollout_authorizations")
