from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping


@dataclass(frozen=True)
class SandboxVerificationRequest:
    operator_user_id: int
    account_id: int
    eligibility_id: int
    provider: str
    provider_configuration_digest: str
    rollout_configuration_digest: str
    checkout_request_digest: str
    webhook_event_digest: str
    provider_mode: str
    rollout_state: str
    provider_validation_current: bool
    preflight_allowed: bool
    account_verified: bool
    eligibility_reserved: bool
    idempotency_key: str
    requested_at: datetime


@dataclass(frozen=True)
class SandboxVerificationDecision:
    allowed: bool
    reason_code: str
    verification_digest: str


def sandbox_verification_digest(request: SandboxVerificationRequest) -> str:
    payload: Mapping[str, object] = {
        "operator_user_id": request.operator_user_id,
        "account_id": request.account_id,
        "eligibility_id": request.eligibility_id,
        "provider": request.provider,
        "provider_configuration_digest": request.provider_configuration_digest,
        "rollout_configuration_digest": request.rollout_configuration_digest,
        "checkout_request_digest": request.checkout_request_digest,
        "webhook_event_digest": request.webhook_event_digest,
        "provider_mode": request.provider_mode,
        "rollout_state": request.rollout_state,
        "idempotency_key": request.idempotency_key,
        "requested_at": request.requested_at.isoformat(),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def evaluate_sandbox_verification(request: SandboxVerificationRequest) -> SandboxVerificationDecision:
    digest = sandbox_verification_digest(request)

    def deny(reason_code: str) -> SandboxVerificationDecision:
        return SandboxVerificationDecision(False, reason_code, digest)

    if request.operator_user_id <= 0:
        return deny("operator_required")
    if request.account_id <= 0 or request.eligibility_id <= 0:
        return deny("account_or_eligibility_invalid")
    if request.provider_mode != "sandbox":
        return deny("sandbox_mode_required")
    if request.rollout_state != "internal":
        return deny("internal_rollout_required")
    if not request.provider_validation_current:
        return deny("provider_validation_not_current")
    if not request.preflight_allowed:
        return deny("promotion_preflight_denied")
    if not request.account_verified:
        return deny("account_not_verified")
    if not request.eligibility_reserved:
        return deny("eligibility_not_reserved")
    if not request.idempotency_key.strip():
        return deny("idempotency_key_required")
    if not all(
        value and len(value) == 64
        for value in (
            request.provider_configuration_digest,
            request.rollout_configuration_digest,
            request.checkout_request_digest,
            request.webhook_event_digest,
        )
    ):
        return deny("verification_evidence_digest_invalid")
    return SandboxVerificationDecision(True, "sandbox_verification_allowed", digest)
