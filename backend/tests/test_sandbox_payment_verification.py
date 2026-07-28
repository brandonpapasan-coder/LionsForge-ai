from dataclasses import replace
from datetime import datetime

import pytest

from app.services.sandbox_payment_verification import (
    SandboxVerificationRequest,
    evaluate_sandbox_verification,
    sandbox_verification_digest,
)


@pytest.fixture
def verification_request() -> SandboxVerificationRequest:
    return SandboxVerificationRequest(
        operator_user_id=7,
        account_id=11,
        eligibility_id=13,
        provider="stripe",
        provider_configuration_digest="a" * 64,
        rollout_configuration_digest="b" * 64,
        checkout_request_digest="c" * 64,
        provider_mode="sandbox",
        rollout_state="internal",
        idempotency_key="sandbox-verification-1",
        requested_at=datetime(2026, 7, 28, 12, 0),
    )


def test_complete_internal_sandbox_request_is_allowed(
    verification_request: SandboxVerificationRequest,
) -> None:
    decision = evaluate_sandbox_verification(verification_request)
    assert decision.allowed is True
    assert decision.reason_code == "sandbox_verification_allowed"
    assert decision.verification_digest == sandbox_verification_digest(verification_request)


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"operator_user_id": 0}, "operator_required"),
        ({"account_id": 0}, "account_or_eligibility_invalid"),
        ({"provider_mode": "live"}, "sandbox_mode_required"),
        ({"rollout_state": "beta"}, "internal_rollout_required"),
        ({"idempotency_key": " "}, "idempotency_key_required"),
        ({"checkout_request_digest": "short"}, "verification_evidence_digest_invalid"),
    ],
)
def test_verification_fails_closed(
    verification_request: SandboxVerificationRequest,
    changes: dict[str, object],
    reason: str,
) -> None:
    decision = evaluate_sandbox_verification(replace(verification_request, **changes))
    assert decision.allowed is False
    assert decision.reason_code == reason


def test_digest_changes_when_authoritative_checkout_evidence_changes(
    verification_request: SandboxVerificationRequest,
) -> None:
    changed = replace(verification_request, checkout_request_digest="e" * 64)
    assert sandbox_verification_digest(verification_request) != sandbox_verification_digest(changed)
