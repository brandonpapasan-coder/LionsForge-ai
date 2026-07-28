from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.promotion_rollout import (
    PromotionCheckoutRequest,
    PromotionProviderEvent,
    PromotionRolloutAuthorization,
)
from app.services.promotion_entitlements import PromotionConflictError, PromotionUnavailableError, append_audit_record
from app.services.promotion_rollout import PromotionGateSnapshot, PromotionRolloutState, rollout_configuration_digest

SUPPORTED_PROVIDER_EVENTS = {
    "checkout.session.completed",
    "invoice.payment_failed",
    "invoice.payment_succeeded",
    "charge.refunded",
    "charge.dispute.created",
    "customer.subscription.deleted",
}


def _digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def authorize_rollout_state(
    db: Session,
    *,
    rollout_state: PromotionRolloutState,
    gates: PromotionGateSnapshot,
    actor_type: str,
    actor_reference: str,
    reason_code: str,
    authorized_at: datetime,
) -> PromotionRolloutAuthorization:
    if rollout_state not in {PromotionRolloutState.DISABLED, PromotionRolloutState.PAUSED}:
        if not gates.promotions_enabled or not gates.paid_beta_authorized or not gates.provider_ready:
            raise PromotionUnavailableError("rollout authorization requires all commercial and provider gates")
    configuration_digest = rollout_configuration_digest(rollout_state=rollout_state, gates=gates)
    authorization = PromotionRolloutAuthorization(
        rollout_state=rollout_state.value,
        actor_type=actor_type,
        actor_reference=actor_reference,
        reason_code=reason_code,
        configuration_digest=configuration_digest,
        authorized_at=authorized_at,
    )
    db.add(authorization)
    db.flush()
    append_audit_record(
        db,
        event_type="promotion_rollout_authorized",
        reason_code=reason_code,
        actor_type=actor_type,
        actor_reference=actor_reference,
        occurred_at=authorized_at,
        payload={"rollout_state": rollout_state.value, "configuration_digest": configuration_digest},
    )
    return authorization


def reserve_checkout_request(
    db: Session,
    *,
    eligibility_id: int,
    provider: str,
    idempotency_key: str,
    request_payload: dict[str, Any],
    created_at: datetime,
) -> PromotionCheckoutRequest:
    request_digest = _digest(request_payload)
    existing = db.execute(
        select(PromotionCheckoutRequest).where(
            PromotionCheckoutRequest.provider == provider,
            PromotionCheckoutRequest.idempotency_key == idempotency_key,
        )
    ).scalar_one_or_none()
    if existing is not None:
        if existing.eligibility_id != eligibility_id or existing.request_digest != request_digest:
            raise PromotionConflictError("checkout idempotency key was reused with different request data")
        return existing
    record = PromotionCheckoutRequest(
        eligibility_id=eligibility_id,
        provider=provider,
        idempotency_key=idempotency_key,
        request_digest=request_digest,
        status="reserved",
        created_at=created_at,
    )
    db.add(record)
    db.flush()
    return record


def ingest_provider_event(
    db: Session,
    *,
    provider: str,
    provider_event_id: str,
    event_type: str,
    payload: dict[str, Any],
    signature_verified: bool,
    received_at: datetime,
) -> tuple[PromotionProviderEvent, bool]:
    if not signature_verified:
        raise PromotionUnavailableError("provider signature verification failed")
    payload_digest = _digest(payload)
    existing = db.execute(
        select(PromotionProviderEvent).where(
            PromotionProviderEvent.provider == provider,
            PromotionProviderEvent.provider_event_id == provider_event_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        if existing.payload_digest != payload_digest or existing.event_type != event_type:
            raise PromotionConflictError("provider event identifier was replayed with different content")
        return existing, True
    if event_type not in SUPPORTED_PROVIDER_EVENTS:
        processing_status = "rejected"
        result = {"reason_code": "unsupported_provider_event"}
    else:
        processing_status = "accepted"
        result = {"reason_code": "provider_event_verified"}
    record = PromotionProviderEvent(
        provider=provider,
        provider_event_id=provider_event_id,
        event_type=event_type,
        payload_digest=payload_digest,
        signature_verified=True,
        processing_status=processing_status,
        processing_result=result,
        received_at=received_at,
    )
    db.add(record)
    db.flush()
    return record, False
