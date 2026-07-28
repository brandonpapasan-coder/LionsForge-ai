"""scope sandbox verification idempotency by operator

Revision ID: 0041_scope_verify_idem
Revises: 0040_sandbox_payment_verify
"""

from alembic import op

revision = "0041_scope_verify_idem"
down_revision = "0040_sandbox_payment_verify"
branch_labels = None
depends_on = None


OLD_CONSTRAINT = "uq_sandbox_payment_verification_idempotency"
NEW_CONSTRAINT = "uq_sandbox_payment_verification_operator_idempotency"
TABLE = "sandbox_payment_verification_runs"


def upgrade() -> None:
    op.drop_constraint(OLD_CONSTRAINT, TABLE, type_="unique")
    op.create_unique_constraint(NEW_CONSTRAINT, TABLE, ["operator_user_id", "idempotency_key"])


def downgrade() -> None:
    op.drop_constraint(NEW_CONSTRAINT, TABLE, type_="unique")
    op.create_unique_constraint(OLD_CONSTRAINT, TABLE, ["idempotency_key"])
