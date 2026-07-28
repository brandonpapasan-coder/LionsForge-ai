from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.payment_provider import PaymentProviderValidation
from app.models.promotion import PromotionEligibility
from app.models.promotion_rollout import PromotionCheckoutRequest, PromotionRolloutAuthorization
from app.services.promotion_entitlements import PromotionUnavailableError
from app.services.sandbox_payment_verification import SandboxVerificationRequest


def derive_sandbox_verification_request(
    db: Session,
    *,
    operator_user_id: int,
    account_id: int,
    eligibility_id: int,
    checkout_request_id: int,
    idempotency_key: str,
    requested_at: datetime,
) -> SandboxVerificationRequest:
    eligibility = db.get(PromotionEligibility, eligibility_id)
    if eligibility is None:
        raise PromotionUnavailableError("sandbox verification eligibility was not found")
    if eligibility.status != "reserved":
        raise PromotionUnavailableError("sandbox verification eligibility is not reserved")
    if eligibility.reserved_until is None or eligibility.reserved_until <= requested_at:
        raise PromotionUnavailableError("sandbox verification eligibility reservation expired")
    if eligibility.verified_account_id != str(account_id):
        raise PromotionUnavailableError("sandbox verification account does not match eligibility")

    checkout = db.get(PromotionCheckoutRequest, checkout_request_id)
    if checkout is None:
        raise PromotionUnavailableError("sandbox verification checkout reservation was not found")
    if checkout.eligibility_id != eligibility.id:
        raise PromotionUnavailableError("sandbox verification checkout does not match eligibility")
    if checkout.status != "reserved":
        raise PromotionUnavailableError("sandbox verification checkout is not reserved")

    provider_validation = db.scalar(
        select(PaymentProviderValidation)
        .where(PaymentProviderValidation.provider == checkout.provider)
        .order_by(PaymentProviderValidation.validated_at.desc(), PaymentProviderValidation.id.desc())
        .limit(1)
    )
    if provider_validation is None:
        raise PromotionUnavailableError("sandbox provider validation was not found")
    if provider_validation.mode != "sandbox":
        raise PromotionUnavailableError("sandbox provider mode is required")
    if provider_validation.validation_status != "validated":
        raise PromotionUnavailableError("sandbox provider validation is not approved")
    if provider_validation.expires_at <= requested_at:
        raise PromotionUnavailableError("sandbox provider validation expired")
    if not (
        provider_validation.api_reference_present
        and provider_validation.webhook_reference_present
        and provider_validation.price_references_present
    ):
        raise PromotionUnavailableError("sandbox provider validation references are incomplete")

    rollout = db.scalar(
        select(PromotionRolloutAuthorization)
        .order_by(PromotionRolloutAuthorization.authorized_at.desc(), PromotionRolloutAuthorization.id.desc())
        .limit(1)
    )
    if rollout is None or rollout.rollout_state != "internal":
        raise PromotionUnavailableError("internal sandbox rollout authorization is required")

    return SandboxVerificationRequest(
        operator_user_id=operator_user_id,
        account_id=account_id,
        eligibility_id=eligibility.id,
        provider=checkout.provider,
        provider_configuration_digest=provider_validation.configuration_digest,
        rollout_configuration_digest=rollout.configuration_digest,
        checkout_request_digest=checkout.request_digest,
        provider_mode=provider_validation.mode,
        rollout_state=rollout.rollout_state,
        idempotency_key=idempotency_key,
        requested_at=requested_at,
    )
