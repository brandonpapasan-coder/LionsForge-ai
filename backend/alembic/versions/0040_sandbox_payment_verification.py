"""add sandbox payment verification records

Revision ID: 0040_sandbox_payment_verification
Revises: 0039_provider_validation
"""

from alembic import op
import sqlalchemy as sa

revision = "0040_sandbox_payment_verification"
down_revision = "0039_provider_validation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sandbox_payment_verification_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("eligibility_id", sa.Integer(), sa.ForeignKey("promotion_eligibilities.id"), nullable=False),
        sa.Column("checkout_request_id", sa.Integer(), sa.ForeignKey("promotion_checkout_requests.id")),
        sa.Column("operator_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_digest", sa.String(length=64), nullable=False),
        sa.Column("provider_configuration_digest", sa.String(length=64), nullable=False),
        sa.Column("rollout_configuration_digest", sa.String(length=64), nullable=False),
        sa.Column("evidence_digest", sa.String(length=64)),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason_code", sa.String(length=96), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_sandbox_payment_verification_idempotency"),
    )
    op.create_index("ix_sandbox_payment_verification_account", "sandbox_payment_verification_runs", ["account_id"])
    op.create_index("ix_sandbox_payment_verification_eligibility", "sandbox_payment_verification_runs", ["eligibility_id"])
    op.create_index("ix_sandbox_payment_verification_started", "sandbox_payment_verification_runs", ["started_at"])
    op.create_table(
        "sandbox_payment_verification_evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("verification_run_id", sa.Integer(), sa.ForeignKey("sandbox_payment_verification_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("evidence_type", sa.String(length=64), nullable=False),
        sa.Column("evidence_digest", sa.String(length=64), nullable=False),
        sa.Column("redacted_payload", sa.JSON(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("verification_run_id", "evidence_type", name="uq_sandbox_verification_evidence_type"),
    )
    op.create_index("ix_sandbox_verification_evidence_run", "sandbox_payment_verification_evidence", ["verification_run_id"])


def downgrade() -> None:
    op.drop_index("ix_sandbox_verification_evidence_run", table_name="sandbox_payment_verification_evidence")
    op.drop_table("sandbox_payment_verification_evidence")
    op.drop_index("ix_sandbox_payment_verification_started", table_name="sandbox_payment_verification_runs")
    op.drop_index("ix_sandbox_payment_verification_eligibility", table_name="sandbox_payment_verification_runs")
    op.drop_index("ix_sandbox_payment_verification_account", table_name="sandbox_payment_verification_runs")
    op.drop_table("sandbox_payment_verification_runs")
