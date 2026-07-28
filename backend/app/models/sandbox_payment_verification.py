from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class SandboxPaymentVerificationRun(Base):
    __tablename__ = "sandbox_payment_verification_runs"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_sandbox_payment_verification_idempotency"),
        Index("ix_sandbox_payment_verification_account", "account_id"),
        Index("ix_sandbox_payment_verification_eligibility", "eligibility_id"),
        Index("ix_sandbox_payment_verification_started", "started_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, nullable=False)
    eligibility_id: Mapped[int] = mapped_column(ForeignKey("promotion_eligibilities.id"), nullable=False)
    checkout_request_id: Mapped[int | None] = mapped_column(ForeignKey("promotion_checkout_requests.id"))
    operator_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_configuration_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    rollout_configuration_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_digest: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    reason_code: Mapped[str] = mapped_column(String(96), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SandboxPaymentVerificationEvidence(Base):
    __tablename__ = "sandbox_payment_verification_evidence"
    __table_args__ = (
        UniqueConstraint("verification_run_id", "evidence_type", name="uq_sandbox_verification_evidence_type"),
        Index("ix_sandbox_verification_evidence_run", "verification_run_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    verification_run_id: Mapped[int] = mapped_column(
        ForeignKey("sandbox_payment_verification_runs.id", ondelete="CASCADE"), nullable=False
    )
    evidence_type: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    redacted_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
