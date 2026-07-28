from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.payment_provider import PaymentProviderValidation
from app.models.promotion import FoundingSubscriberSequence, PromotionEligibility
from app.models.promotion_rollout import (
    PromotionCheckoutRequest,
    PromotionProviderEvent,
    PromotionRolloutAuthorization,
)
from app.services.promotion_rollout import PromotionGateSnapshot, PromotionRolloutState


@dataclass(frozen=True)
class PromotionRolloutStatus:
    rollout_state: str
    configuration_digest: str | None
    authorized_at: datetime | None
    authorized_by: str | None
    reason_code: str | None
    gates: dict[str, bool]
    provider_validation_status: str | None
    provider_validation_reason: str | None
    provider_validation_digest: str | None
    provider_validated_at: datetime | None
    provider_validation_expires_at: datetime | None
    reserved_eligibilities: int
    active_eligibilities: int
    grace_eligibilities: int
    expired_eligibilities: int
    founding_reserved_positions: int
    founding_consumed_positions: int
    founding_released_positions: int
    checkout_requests_reserved: int
    checkout_requests_completed: int
    provider_events_accepted: int
    provider_events_rejected: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _count(db: Session, model, field, value: str) -> int:
    return int(db.scalar(select(func.count()).select_from(model).where(field == value)) or 0)


def read_promotion_rollout_status(
    db: Session,
    *,
    gates: PromotionGateSnapshot,
) -> PromotionRolloutStatus:
    latest = db.scalar(
        select(PromotionRolloutAuthorization)
        .order_by(PromotionRolloutAuthorization.authorized_at.desc(), PromotionRolloutAuthorization.id.desc())
        .limit(1)
    )
    provider_validation = db.scalar(
        select(PaymentProviderValidation)
        .order_by(PaymentProviderValidation.validated_at.desc(), PaymentProviderValidation.id.desc())
        .limit(1)
    )
    rollout_state = latest.rollout_state if latest is not None else PromotionRolloutState.DISABLED.value
    return PromotionRolloutStatus(
        rollout_state=rollout_state,
        configuration_digest=latest.configuration_digest if latest else None,
        authorized_at=latest.authorized_at if latest else None,
        authorized_by=latest.actor_reference if latest else None,
        reason_code=latest.reason_code if latest else None,
        gates={
            "promotions_enabled": gates.promotions_enabled,
            "paid_beta_authorized": gates.paid_beta_authorized,
            "beta_lifetime_discount_enabled": gates.beta_lifetime_discount_enabled,
            "founding_subscriber_enrollment_enabled": gates.founding_subscriber_enrollment_enabled,
            "provider_ready": gates.provider_ready,
        },
        provider_validation_status=provider_validation.validation_status if provider_validation else None,
        provider_validation_reason=provider_validation.reason_code if provider_validation else None,
        provider_validation_digest=provider_validation.configuration_digest if provider_validation else None,
        provider_validated_at=provider_validation.validated_at if provider_validation else None,
        provider_validation_expires_at=provider_validation.expires_at if provider_validation else None,
        reserved_eligibilities=_count(db, PromotionEligibility, PromotionEligibility.status, "reserved"),
        active_eligibilities=_count(db, PromotionEligibility, PromotionEligibility.status, "active"),
        grace_eligibilities=_count(db, PromotionEligibility, PromotionEligibility.status, "grace"),
        expired_eligibilities=_count(db, PromotionEligibility, PromotionEligibility.status, "expired"),
        founding_reserved_positions=_count(
            db, FoundingSubscriberSequence, FoundingSubscriberSequence.allocation_status, "reserved"
        ),
        founding_consumed_positions=_count(
            db, FoundingSubscriberSequence, FoundingSubscriberSequence.allocation_status, "consumed"
        ),
        founding_released_positions=_count(
            db, FoundingSubscriberSequence, FoundingSubscriberSequence.allocation_status, "released"
        ),
        checkout_requests_reserved=_count(
            db, PromotionCheckoutRequest, PromotionCheckoutRequest.status, "reserved"
        ),
        checkout_requests_completed=_count(
            db, PromotionCheckoutRequest, PromotionCheckoutRequest.status, "completed"
        ),
        provider_events_accepted=_count(
            db, PromotionProviderEvent, PromotionProviderEvent.processing_status, "accepted"
        ),
        provider_events_rejected=_count(
            db, PromotionProviderEvent, PromotionProviderEvent.processing_status, "rejected"
        ),
    )
