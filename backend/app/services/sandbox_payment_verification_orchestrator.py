from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.sandbox_payment_verification import SandboxPaymentVerificationEvidence
from app.services.promotion_entitlements import PromotionUnavailableError
from app.services.sandbox_payment_verification import (
    SandboxVerificationRequest,
    evaluate_sandbox_verification,
)
from app.services.sandbox_payment_verification_persistence import (
    append_verification_evidence,
    complete_verification_run,
    reserve_verification_run,
)


class SandboxCheckoutExecutor(Protocol):
    def create_session(self, *, idempotency_key: str) -> Mapping[str, object]: ...


class SyntheticWebhookVerifier(Protocol):
    def verify(self, *, provider_session_id: str) -> Mapping[str, object]: ...


@dataclass(frozen=True)
class SandboxVerificationResult:
    verification_run_id: int
    checkout_request_id: int
    provider_session_id: str
    evidence_digest: str
    status: str


def _read_completed_checkout_evidence(
    db: Session,
    *,
    verification_run_id: int,
    checkout_request_id: int,
) -> str:
    evidence = db.scalar(
        select(SandboxPaymentVerificationEvidence).where(
            SandboxPaymentVerificationEvidence.verification_run_id == verification_run_id,
            SandboxPaymentVerificationEvidence.evidence_type == "sandbox_checkout",
        )
    )
    if evidence is None:
        raise PromotionUnavailableError("stored sandbox checkout evidence is missing")

    stored_checkout_request_id = evidence.redacted_payload.get("checkout_request_id")
    provider_session_id = evidence.redacted_payload.get("provider_session_id")
    if stored_checkout_request_id != checkout_request_id:
        raise PromotionUnavailableError("stored sandbox checkout evidence does not match reservation")
    if not isinstance(provider_session_id, str) or not provider_session_id:
        raise PromotionUnavailableError("stored sandbox checkout evidence omitted session id")
    return provider_session_id


def execute_sandbox_payment_verification(
    db: Session,
    *,
    request: SandboxVerificationRequest,
    checkout_request_id: int,
    checkout_executor: SandboxCheckoutExecutor,
    webhook_verifier: SyntheticWebhookVerifier,
    now: datetime,
) -> SandboxVerificationResult:
    decision = evaluate_sandbox_verification(request)
    if not decision.allowed:
        raise PromotionUnavailableError(f"sandbox verification denied: {decision.reason_code}")
    if checkout_request_id <= 0:
        raise PromotionUnavailableError("sandbox verification requires a checkout reservation")

    payload = {
        "verification_digest": decision.verification_digest,
        "checkout_request_digest": request.checkout_request_digest,
    }

    with db.begin_nested():
        run = reserve_verification_run(
            db,
            account_id=request.account_id,
            eligibility_id=request.eligibility_id,
            operator_user_id=request.operator_user_id,
            provider=request.provider,
            idempotency_key=request.idempotency_key,
            provider_configuration_digest=request.provider_configuration_digest,
            rollout_configuration_digest=request.rollout_configuration_digest,
            request_payload=payload,
            started_at=now,
        )

        if run.status == "completed":
            if run.checkout_request_id != checkout_request_id or not run.evidence_digest:
                raise PromotionUnavailableError("stored sandbox verification is incomplete")
            provider_session_id = _read_completed_checkout_evidence(
                db,
                verification_run_id=run.id,
                checkout_request_id=checkout_request_id,
            )
            return SandboxVerificationResult(
                verification_run_id=run.id,
                checkout_request_id=checkout_request_id,
                provider_session_id=provider_session_id,
                evidence_digest=run.evidence_digest,
                status=run.status,
            )

        checkout = checkout_executor.create_session(idempotency_key=request.idempotency_key)
        provider_session_id = checkout.get("id")
        checkout_status = checkout.get("status", "created")
        if not isinstance(provider_session_id, str) or not provider_session_id:
            raise PromotionUnavailableError("sandbox checkout response omitted session id")
        if not isinstance(checkout_status, str):
            raise PromotionUnavailableError("sandbox checkout response status is invalid")

        checkout_evidence = append_verification_evidence(
            db,
            run=run,
            evidence_type="sandbox_checkout",
            redacted_payload={
                "provider": request.provider,
                "provider_session_id": provider_session_id,
                "status": checkout_status,
                "checkout_request_id": checkout_request_id,
            },
            recorded_at=now,
        )

        webhook = webhook_verifier.verify(provider_session_id=provider_session_id)
        verified = webhook.get("verified")
        event_type = webhook.get("event_type")
        event_digest = webhook.get("event_digest")
        if verified is not True:
            raise PromotionUnavailableError("synthetic webhook verification failed")
        if not isinstance(event_type, str) or not event_type:
            raise PromotionUnavailableError("synthetic webhook event type is invalid")
        if not isinstance(event_digest, str) or len(event_digest) != 64:
            raise PromotionUnavailableError("synthetic webhook event digest is invalid")

        webhook_evidence = append_verification_evidence(
            db,
            run=run,
            evidence_type="synthetic_webhook",
            redacted_payload={
                "event_type": event_type,
                "event_digest": event_digest,
                "verified": True,
            },
            recorded_at=now,
        )

        completed = complete_verification_run(
            db,
            run=run,
            evidence_digests=[checkout_evidence.evidence_digest, webhook_evidence.evidence_digest],
            checkout_request_id=checkout_request_id,
            completed_at=now,
        )

    if not completed.evidence_digest:
        raise PromotionUnavailableError("sandbox verification evidence digest is unavailable")
    return SandboxVerificationResult(
        verification_run_id=completed.id,
        checkout_request_id=checkout_request_id,
        provider_session_id=provider_session_id,
        evidence_digest=completed.evidence_digest,
        status=completed.status,
    )
