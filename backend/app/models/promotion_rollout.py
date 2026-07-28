from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class PromotionRolloutAuthorization(Base):
    __tablename__ = "promotion_rollout_authorizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    rollout_state: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_reference: Mapped[str] = mapped_column(String(120), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(80), nullable=False)
    configuration_digest: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    authorized_at: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)


class PromotionCheckoutRequest(Base):
    __tablename__ = "promotion_checkout_requests"
    __table_args__ = (
        UniqueConstraint("provider", "idempotency_key", name="uq_promotion_checkout_provider_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    eligibility_id: Mapped[int] = mapped_column(ForeignKey("promotion_eligibilities.id"), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_session_id: Mapped[str | None] = mapped_column(String(160), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class PromotionProviderEvent(Base):
    __tablename__ = "promotion_provider_events"
    __table_args__ = (
        UniqueConstraint("provider", "provider_event_id", name="uq_promotion_provider_event"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(160), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    payload_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    signature_verified: Mapped[bool] = mapped_column(nullable=False)
    processing_status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    processing_result: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
