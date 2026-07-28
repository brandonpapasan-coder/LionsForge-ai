from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.payment_provider import PaymentProviderValidation
from app.services.payment_provider_readiness import (
    ProviderReadinessDecision,
    ProviderReferenceSet,
    VALIDATION_MAX_AGE,
)
from app.services.promotion_entitlements import append_audit_record

WEBHOOK_TIMESTAMP_TOLERANCE = timedelta(minutes=5)


def record_provider_validation(
    db: Session,
    *,
    references: ProviderReferenceSet,
    decision: ProviderReadinessDecision,
    actor_type: str,
    actor_reference: str,
    validated_at: datetime,
) -> PaymentProviderValidation:
    record = PaymentProviderValidation(
        provider=references.provider,
        mode=references.mode.value,
        configuration_digest=decision.configuration_digest,
        validation_status="valid" if decision.ready else "invalid",
        reason_code=decision.reason_code,
        validated_at=validated_at,
        expires_at=validated_at + VALIDATION_MAX_AGE,
        api_reference_present=bool(references.api_credential_reference),
        webhook_reference_present=bool(references.webhook_secret_reference),
        price_references_present=bool(references.beta_price_reference and references.founding_price_reference),
        details={"currency": references.currency.upper(), "account_mode": references.account_mode.value},
    )
    db.add(record)
    db.flush()
    append_audit_record(
        db,
        event_type="payment_provider_validation_recorded",
        reason_code=decision.reason_code,
        actor_type=actor_type,
        actor_reference=actor_reference,
        occurred_at=validated_at,
        payload={
            "provider": references.provider,
            "mode": references.mode.value,
            "configuration_digest": decision.configuration_digest,
            "validation_status": record.validation_status,
        },
    )
    return record


def verify_webhook_signature(
    *,
    payload: bytes,
    signature_hex: str,
    timestamp: datetime,
    now: datetime,
    secret: bytes,
) -> bool:
    if timestamp > now + WEBHOOK_TIMESTAMP_TOLERANCE:
        return False
    if now - timestamp > WEBHOOK_TIMESTAMP_TOLERANCE:
        return False
    signed = str(int(timestamp.timestamp())).encode("ascii") + b"." + payload
    expected = hmac.new(secret, signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_hex)
