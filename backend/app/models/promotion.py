from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class PromotionCampaign(Base):
    __tablename__ = "promotion_campaigns"
    __table_args__ = (
        CheckConstraint("discount_percent > 0 AND discount_percent <= 100", name="ck_promotion_campaign_discount"),
        CheckConstraint("capacity IS NULL OR capacity > 0", name="ck_promotion_campaign_capacity"),
        UniqueConstraint("slug", name="uq_promotion_campaign_slug"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    promotion_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    discount_percent: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_months: Mapped[int | None] = mapped_column(Integer)
    capacity: Mapped[int | None] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class PromotionEligibility(Base):
    __tablename__ = "promotion_eligibilities"
    __table_args__ = (
        UniqueConstraint("campaign_id", "user_id", name="uq_promotion_eligibility_campaign_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("promotion_campaigns.id"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    verified_account_id: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    reserved_until: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    eligibility_reason: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class FoundingSubscriberSequence(Base):
    __tablename__ = "founding_subscriber_sequences"
    __table_args__ = (
        UniqueConstraint("campaign_id", "position", name="uq_founding_sequence_campaign_position"),
        UniqueConstraint("campaign_id", "eligibility_id", name="uq_founding_sequence_campaign_eligibility"),
        CheckConstraint("position > 0 AND position <= 20000", name="ck_founding_sequence_position"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("promotion_campaigns.id"), index=True, nullable=False)
    eligibility_id: Mapped[int] = mapped_column(ForeignKey("promotion_eligibilities.id"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    allocation_status: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    reserved_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime)


class PromotionRedemption(Base):
    __tablename__ = "promotion_redemptions"
    __table_args__ = (
        UniqueConstraint("provider", "provider_subscription_id", name="uq_promotion_redemption_provider_subscription"),
        UniqueConstraint("eligibility_id", name="uq_promotion_redemption_eligibility"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    eligibility_id: Mapped[int] = mapped_column(ForeignKey("promotion_eligibilities.id"), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_customer_id: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    provider_subscription_id: Mapped[str] = mapped_column(String(160), nullable=False)
    provider_discount_id: Mapped[str | None] = mapped_column(String(160))
    internal_entitlement_id: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)


class SubscriptionPriceProtection(Base):
    __tablename__ = "subscription_price_protections"
    __table_args__ = (
        UniqueConstraint("redemption_id", name="uq_subscription_price_protection_redemption"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    redemption_id: Mapped[int] = mapped_column(ForeignKey("promotion_redemptions.id"), nullable=False)
    protection_type: Mapped[str] = mapped_column(String(32), nullable=False)
    protected_percent: Mapped[int] = mapped_column(Integer, nullable=False)
    protected_until: Mapped[datetime | None] = mapped_column(DateTime)
    continuous_subscription_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    grace_period_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    regular_price_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    regular_price_currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    regular_price_effective_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)


class PromotionAuditRecord(Base):
    __tablename__ = "promotion_audit_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey("promotion_campaigns.id"), index=True)
    eligibility_id: Mapped[int | None] = mapped_column(ForeignKey("promotion_eligibilities.id"), index=True)
    redemption_id: Mapped[int | None] = mapped_column(ForeignKey("promotion_redemptions.id"), index=True)
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_reference: Mapped[str | None] = mapped_column(String(120))
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    reason_code: Mapped[str] = mapped_column(String(80), nullable=False)
    event_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    previous_record_sha256: Mapped[str | None] = mapped_column(String(64))
    record_sha256: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
