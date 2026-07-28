from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.promotion_rollout import PromotionCheckoutRequest
from app.services.payment_provider_readiness import (
    CheckoutProviderAdapter,
    InternalCheckoutRequest,
    NormalizedCheckoutSession,
    ProviderReadinessDecision,
    ProviderReferenceSet,
    create_internal_checkout_session,
)
from app.services.promotion_entitlements import PromotionConflictError, PromotionUnavailableError
from app.services.promotion_rollout import CheckoutPreflightDecision
from app.services.promotion_rollout_persistence import reserve_checkout_request


@dataclass(frozen=True)
class CheckoutOrchestrationResult:
    checkout_request_id: int
    provider_session_id: str
    checkout_url: str
    status: str
    provider: str
    replayed_reservation: bool


def orchestrate_internal_checkout(
    db: Session,
    *,
    preflight: CheckoutPreflightDecision,
    references: ProviderReferenceSet,
    readiness: ProviderReadinessDecision,
    request: InternalCheckoutRequest,
    adapter: CheckoutProviderAdapter,
    created_at: datetime,
) -> CheckoutOrchestrationResult:
    """Create one sandbox checkout session with rollback-safe local persistence.

    The provider call remains idempotent through ``request.idempotency_key``. Any
    local failure rolls back the reservation/session binding savepoint, so a
    partially bound provider session cannot be committed by this service.
    """
    if not preflight.allowed:
        raise PromotionUnavailableError(f"checkout preflight denied: {preflight.reason_code}")
    if not readiness.ready:
        raise PromotionUnavailableError(f"provider not ready: {readiness.reason_code}")
    if request.account_id <= 0 or request.eligibility_id <= 0:
        raise PromotionUnavailableError("checkout requires account-bound eligibility")
    if request.amount_minor <= 0:
        raise PromotionUnavailableError("checkout amount must be positive")
    if request.metadata.get("account_id") != str(request.account_id):
        raise PromotionConflictError("checkout metadata account binding mismatch")
    if request.metadata.get("eligibility_id") != str(request.eligibility_id):
        raise PromotionConflictError("checkout metadata eligibility binding mismatch")

    request_payload = {
        "account_id": request.account_id,
        "eligibility_id": request.eligibility_id,
        "promotion_type": request.promotion_type,
        "amount_minor": request.amount_minor,
        "currency": request.currency.upper(),
        "success_url": request.success_url,
        "cancel_url": request.cancel_url,
        "metadata": dict(sorted(request.metadata.items())),
        "provider_configuration_digest": readiness.configuration_digest,
        "preflight_configuration_digest": preflight.configuration_digest,
    }

    with db.begin_nested():
        checkout_record = reserve_checkout_request(
            db,
            eligibility_id=request.eligibility_id,
            provider=references.provider,
            idempotency_key=request.idempotency_key,
            request_payload=request_payload,
            created_at=created_at,
        )
        replayed_reservation = checkout_record.id is not None and checkout_record.status != "reserved"

        session = create_internal_checkout_session(
            references=references,
            readiness=readiness,
            request=request,
            adapter=adapter,
        )
        _bind_provider_session(checkout_record, session)
        db.flush()

    return CheckoutOrchestrationResult(
        checkout_request_id=checkout_record.id,
        provider_session_id=session.provider_session_id,
        checkout_url=session.checkout_url,
        status=session.status,
        provider=session.provider,
        replayed_reservation=replayed_reservation,
    )


def _bind_provider_session(
    checkout_record: PromotionCheckoutRequest,
    session: NormalizedCheckoutSession,
) -> None:
    if checkout_record.provider_session_id is not None and checkout_record.provider_session_id != session.provider_session_id:
        raise PromotionConflictError("idempotent checkout returned a different provider session")
    checkout_record.provider_session_id = session.provider_session_id
    checkout_record.status = "completed"
