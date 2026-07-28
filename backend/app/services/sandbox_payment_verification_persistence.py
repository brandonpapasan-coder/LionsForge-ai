from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.sandbox_payment_verification import (
    SandboxPaymentVerificationEvidence,
    SandboxPaymentVerificationRun,
)
from app.services.promotion_entitlements import PromotionConflictError, append_audit_record

VERIFICATION_TTL = timedelta(hours=24)


def _digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def reserve_verification_run(
    db: Session,
    *,
    account_id: int,
    eligibility_id: int,
    operator_user_id: int,
    provider: str,
    idempotency_key: str,
    provider_configuration_digest: str,
    rollout_configuration_digest: str,
    request_payload: dict[str, Any],
    started_at: datetime,
) -> SandboxPaymentVerificationRun:
    request_digest = _digest(request_payload)
    existing = db.scalar(
        select(SandboxPaymentVerificationRun).where(
            SandboxPaymentVerificationRun.idempotency_key == idempotency_key
        )
    )
    if existing is not None:
        if (
            existing.account_id != account_id
            or existing.eligibility_id != eligibility_id
            or existing.operator_user_id != operator_user_id
            or existing.request_digest != request_digest
        ):
            raise PromotionConflictError("sandbox verification idempotency key was reused with different data")
        return existing

    run = SandboxPaymentVerificationRun(
        account_id=account_id,
        eligibility_id=eligibility_id,
        operator_user_id=operator_user_id,
        provider=provider,
        idempotency_key=idempotency_key,
        request_digest=request_digest,
        provider_configuration_digest=provider_configuration_digest,
        rollout_configuration_digest=rollout_configuration_digest,
        status="pending",
        reason_code="verification_reserved",
        started_at=started_at,
        expires_at=started_at + VERIFICATION_TTL,
    )
    db.add(run)
    db.flush()
    append_audit_record(
        db,
        event_type="sandbox_payment_verification_reserved",
        reason_code="verification_reserved",
        actor_type="operator",
        actor_reference=str(operator_user_id),
        occurred_at=started_at,
        payload={"verification_run_id": run.id, "request_digest": request_digest},
    )
    return run


def append_verification_evidence(
    db: Session,
    *,
    run: SandboxPaymentVerificationRun,
    evidence_type: str,
    redacted_payload: dict[str, Any],
    recorded_at: datetime,
) -> SandboxPaymentVerificationEvidence:
    evidence_digest = _digest(redacted_payload)
    existing = db.scalar(
        select(SandboxPaymentVerificationEvidence).where(
            SandboxPaymentVerificationEvidence.verification_run_id == run.id,
            SandboxPaymentVerificationEvidence.evidence_type == evidence_type,
        )
    )
    if existing is not None:
        if existing.evidence_digest != evidence_digest:
            raise PromotionConflictError("sandbox verification evidence was replayed with different content")
        return existing
    evidence = SandboxPaymentVerificationEvidence(
        verification_run_id=run.id,
        evidence_type=evidence_type,
        evidence_digest=evidence_digest,
        redacted_payload=redacted_payload,
        recorded_at=recorded_at,
    )
    db.add(evidence)
    db.flush()
    return evidence


def complete_verification_run(
    db: Session,
    *,
    run: SandboxPaymentVerificationRun,
    evidence_digests: list[str],
    checkout_request_id: int,
    completed_at: datetime,
) -> SandboxPaymentVerificationRun:
    final_digest = _digest(
        {
            "run_id": run.id,
            "request_digest": run.request_digest,
            "provider_configuration_digest": run.provider_configuration_digest,
            "rollout_configuration_digest": run.rollout_configuration_digest,
            "evidence_digests": sorted(evidence_digests),
        }
    )
    if run.status == "completed":
        if run.evidence_digest != final_digest or run.checkout_request_id != checkout_request_id:
            raise PromotionConflictError("completed sandbox verification does not match stored evidence")
        return run
    run.checkout_request_id = checkout_request_id
    run.evidence_digest = final_digest
    run.status = "completed"
    run.reason_code = "sandbox_verification_completed"
    run.completed_at = completed_at
    append_audit_record(
        db,
        event_type="sandbox_payment_verification_completed",
        reason_code=run.reason_code,
        actor_type="operator",
        actor_reference=str(run.operator_user_id),
        occurred_at=completed_at,
        payload={"verification_run_id": run.id, "evidence_digest": final_digest},
    )
    db.flush()
    return run
