from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.promotion import (
    FoundingSubscriberSequence,
    PromotionCampaign,
    PromotionEligibility,
    PromotionRedemption,
    SubscriptionPriceProtection,
)
from app.services.promotion_entitlements import (
    PromotionConflictError,
    PromotionUnavailableError,
    append_audit_record,
    payment_provider_metadata,
)


@dataclass(frozen=True)
class CheckoutDisclosure:
    promotion_name: str
    discounted_price_amount_cents: int
    regular_price_amount_cents: int
    currency: str
    discount_percent: int
    promotional_period_months: int | None
    regular_price_effective_at: datetime | None
    disclosure_text: str


@dataclass(frozen=True)
class ActivationResult:
    redemption_id: int
    entitlement_id: str
    provider_metadata: dict[str, str]


def build_checkout_disclosure(
    *,
    campaign: PromotionCampaign,
    regular_price_amount_cents: int,
    currency: str,
    regular_price_effective_at: datetime | None,
) -> CheckoutDisclosure:
    if regular_price_amount_cents <= 0:
        raise ValueError("regular price must be positive")
    normalized_currency = currency.upper()
    if len(normalized_currency) != 3:
        raise ValueError("currency must be a three-letter code")
    discounted = regular_price_amount_cents * (100 - campaign.discount_percent) // 100
    if campaign.promotion_type == "founding":
        if campaign.duration_months != 12 or regular_price_effective_at is None:
            raise PromotionUnavailableError("founding checkout requires a twelve-month transition date")
        text = (
            f"You pay {campaign.discount_percent}% off for 12 months. "
            f"Beginning {regular_price_effective_at.date().isoformat()}, your subscription renews at the "
            f"regular published price of {normalized_currency} {regular_price_amount_cents / 100:.2f}."
        )
    elif campaign.promotion_type == "beta":
        text = (
            f"You pay {campaign.discount_percent}% off while this verified account subscription remains "
            "continuously active, subject to the failed-payment grace policy."
        )
    else:
        raise PromotionUnavailableError("unsupported promotion type")
    return CheckoutDisclosure(
        promotion_name=campaign.slug,
        discounted_price_amount_cents=discounted,
        regular_price_amount_cents=regular_price_amount_cents,
        currency=normalized_currency,
        discount_percent=campaign.discount_percent,
        promotional_period_months=campaign.duration_months,
        regular_price_effective_at=regular_price_effective_at,
        disclosure_text=text,
    )


def activate_reserved_promotion(
    db: Session,
    *,
    campaign: PromotionCampaign,
    eligibility: PromotionEligibility,
    provider: str,
    provider_customer_id: str,
    provider_subscription_id: str,
    provider_discount_id: str | None,
    regular_price_amount_cents: int,
    currency: str,
    activated_at: datetime,
    regular_price_effective_at: datetime | None,
    grace_period_days: int = 7,
) -> ActivationResult:
    if eligibility.campaign_id != campaign.id or eligibility.status != "reserved":
        raise PromotionConflictError("promotion eligibility is not an activatable reservation")
    if eligibility.reserved_until is None or eligibility.reserved_until < activated_at:
        raise PromotionUnavailableError("promotion reservation has expired")
    if grace_period_days < 0:
        raise ValueError("grace period cannot be negative")

    build_checkout_disclosure(
        campaign=campaign,
        regular_price_amount_cents=regular_price_amount_cents,
        currency=currency,
        regular_price_effective_at=regular_price_effective_at,
    )
    existing = db.execute(
        select(PromotionRedemption.id).where(
            PromotionRedemption.provider == provider,
            PromotionRedemption.provider_subscription_id == provider_subscription_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise PromotionConflictError("provider subscription already has a promotion redemption")

    entitlement_id = f"ent_{uuid4().hex}"
    redemption = PromotionRedemption(
        eligibility_id=eligibility.id,
        provider=provider,
        provider_customer_id=provider_customer_id,
        provider_subscription_id=provider_subscription_id,
        provider_discount_id=provider_discount_id,
        internal_entitlement_id=entitlement_id,
        started_at=activated_at,
        status="active",
    )
    db.add(redemption)
    try:
        db.flush()
        protection = SubscriptionPriceProtection(
            redemption_id=redemption.id,
            protection_type="continuous_lifetime" if campaign.promotion_type == "beta" else "fixed_term",
            protected_percent=campaign.discount_percent,
            protected_until=regular_price_effective_at if campaign.promotion_type == "founding" else None,
            continuous_subscription_required=campaign.promotion_type == "beta",
            grace_period_days=grace_period_days,
            regular_price_amount_cents=regular_price_amount_cents,
            regular_price_currency=currency.upper(),
            regular_price_effective_at=regular_price_effective_at,
            status="active",
        )
        db.add(protection)
        eligibility.status = "active"
        eligibility.reserved_until = None
        sequence = db.execute(
            select(FoundingSubscriberSequence).where(
                FoundingSubscriberSequence.eligibility_id == eligibility.id,
                FoundingSubscriberSequence.allocation_status == "reserved",
            )
        ).scalar_one_or_none()
        if sequence is not None:
            sequence.allocation_status = "consumed"
        append_audit_record(
            db,
            event_type="promotion_activated",
            reason_code="provider_subscription_confirmed",
            actor_type="system",
            occurred_at=activated_at,
            payload={
                "provider": provider,
                "provider_subscription_id": provider_subscription_id,
                "entitlement_id": entitlement_id,
            },
            campaign_id=campaign.id,
            eligibility_id=eligibility.id,
            redemption_id=redemption.id,
        )
        db.flush()
    except IntegrityError as exc:
        raise PromotionConflictError("promotion activation conflicted with existing entitlement state") from exc

    return ActivationResult(
        redemption_id=redemption.id,
        entitlement_id=entitlement_id,
        provider_metadata=payment_provider_metadata(
            eligibility_id=eligibility.id,
            campaign_slug=campaign.slug,
            entitlement_id=entitlement_id,
        ),
    )
