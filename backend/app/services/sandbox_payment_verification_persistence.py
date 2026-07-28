from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.sandbox_payment_verification import (
    SandboxPaymentVerificationEvidence,
    SandboxPaymentVerificationRun,
)
from app.services.promotion_entitlements import PromotionConflictError, append_audit_record

VERIFICATION_TTL = timedelta(hours=24)


def canonical_payload_digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def verification_evidence_chain_digest(
    *,
    run: SandboxPaymentVerificationRun,
    evidence_digests: list[str],
) -> str:
    return canonical_payload_digest(
        {
            "run_id": run.id,
            "request_digest": run.request_digest,
            "provider_configuration_digest": run.provider_configuration_digest,
            "rollout_configuration_digest": run.rollout_configuration_digest,
            "evidence_digests": sorted(evidence_digests),
        }
    )


def _find_verification_run(
    db: Session,
    *,
    operator_user_id: int,
    idempotency_key: str,
) -> SandboxPaymentVerificationRun | None:
    return db.scalar(
        select(SandboxPaymentVerificationRun).where(
            SandboxPaymentVerificationRun.operator_user_id == operator_user_id,
            SandboxPaymentVerificationRun.idempotency_key == idempotency_key,
        )
    )


def _resolve_verification_replay(
    existing: SandboxPaymentVerificationRun,
    *,
    account_id: int,
    eligibility_id: int,
    request_digest: str,
) -> SandboxPaymentVerificationRun:
    if (
        existing.account_id != account_id
        or existing.eligibility_id != eligibility_id
        or existing.request_digest != request_digest
    ):
        raise PromotionConflictError("sandbox verification idempotency key was reused with different data")
    return existing


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
    request_digest = canonical_payload_digest(request_payload)
    existing = _find_verification_run(
        db,
        operator_user_id=operator_user_id,
        idempotency_key=idempotency_key,
    )
    if existing is not None:
        return _resolve_verification_replay(
            existing,
            account_id=account_id,
            eligibility_id=eligibility_id,
            request_digest=request_digest,
        )

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
    try:
        with db.begin_nested():
            db.add(run)
            db.flush()
    except IntegrityError as exc:
        # The savepoint rolls back only this losing insert. The surrounding
        # transaction remains usable so the committed winner can be resolved.
        existing = _find_verification_run(
            db,
            operator_user_id=operator_user_id,
            idempotency_key=idempotency_key,
        )
        if existing is None:
            raise PromotionConflictError(
                "sandbox verification idempotency contention could not be resolved"
            ) from exc
        return _resolve_verification_replay(
            existing,
            account_id=account_id,
            eligibility_id=eligibility_id,
            request_digest=request_digest,
        )

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


def _find_verification_evidence(
    db: Session,
    *,
    verification_run_id: int,
    evidence_type: str,
) -> SandboxPaymentVerificationEvidence | None:
    return db.scalar(
        select(SandboxPaymentVerificationEvidence).where(
            SandboxPaymentVerificationEvidence.verification_run_id == verification_run_id,
            SandboxPaymentVerificationEvidence.evidence_type == evidence_type,
        )
    )


def _resolve_evidence_replay(
    existing: SandboxPaymentVerificationEvidence,
    *,
    evidence_digest: str,
) -> SandboxPaymentVerificationEvidence:
    if existing.evidence_digest != evidence_digest:
        raise PromotionConflictError("sandbox verification evidence was replayed with different content")
    return existing


def append_verification_evidence(
    db: Session,
    *,
    run: SandboxPaymentVerificationRun,
    evidence_type: str,
    redacted_payload: dict[str, Any],
    recorded_at: datetime,
) -> SandboxPaymentVerificationEvidence:
    evidence_digest = canonical_payload_digest(redacted_payload)
    existing = _find_verification_evidence(
        db,
        verification_run_id=run.id,
        evidence_type=evidence_type,
    )
    if existing is not None:
        return _resolve_evidence_replay(existing, evidence_digest=evidence_digest)

    evidence = SandboxPaymentVerificationEvidence(
        verification_run_id=run.id,
        evidence_type=evidence_type,
        evidence_digest=evidence_digest,
        redacted_payload=redacted_payload,
        recorded_at=recorded_at,
    )
    try:
        with db.begin_nested():
            db.add(evidence)
            db.flush()
    except IntegrityError as exc:
        existing = _find_verification_evidence(
            db,
            verification_run_id=run.id,
            evidence_type=evidence_type,
        )
        if existing is None:
            raise PromotionConflictError(
                "sandbox verification evidence contention could not be resolved"
            ) from exc
        return _resolve_evidence_replay(existing, evidence_digest=evidence_digest)
    return evidence


def complete_verification_run(
    db: Session,
    *,
    run: SandboxPaymentVerificationRun,
    evidence_digests: list[str],
    checkout_request_id: int,
    completed_at: datetime,
) -> SandboxPaymentVerificationRun:
    final_digest = verification_evidence_chain_digest(run=run, evidence_digests=evidence_digests)
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
