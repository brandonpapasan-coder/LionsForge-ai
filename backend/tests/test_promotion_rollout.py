import pytest

from app.services.promotion_rollout import (
    CheckoutPreflightRequest,
    PromotionGateSnapshot,
    PromotionRolloutState,
    evaluate_checkout_preflight,
    rollout_configuration_digest,
)


def _gates(**overrides: bool) -> PromotionGateSnapshot:
    values = {
        "promotions_enabled": True,
        "paid_beta_authorized": True,
        "beta_lifetime_discount_enabled": True,
        "founding_subscriber_enrollment_enabled": True,
        "provider_ready": True,
    }
    values.update(overrides)
    return PromotionGateSnapshot(**values)


def _request(**overrides: object) -> CheckoutPreflightRequest:
    values = {
        "rollout_state": PromotionRolloutState.BETA,
        "promotion_type": "beta",
        "is_internal_account": False,
        "account_verified": True,
        "campaign_active": True,
        "has_active_promotion": False,
        "disclosure_acknowledged": True,
        "remaining_capacity": None,
        "gates": _gates(),
    }
    values.update(overrides)
    return CheckoutPreflightRequest(**values)


@pytest.mark.parametrize(
    ("state", "reason"),
    [
        (PromotionRolloutState.DISABLED, "rollout_disabled"),
        (PromotionRolloutState.PAUSED, "rollout_paused"),
    ],
)
def test_disabled_and_paused_states_fail_closed(state: PromotionRolloutState, reason: str) -> None:
    decision = evaluate_checkout_preflight(_request(rollout_state=state))
    assert decision.allowed is False
    assert decision.reason_code == reason


def test_internal_rollout_rejects_non_internal_accounts() -> None:
    decision = evaluate_checkout_preflight(
        _request(rollout_state=PromotionRolloutState.INTERNAL, is_internal_account=False)
    )
    assert decision.allowed is False
    assert decision.reason_code == "internal_account_required"


def test_beta_rollout_approves_only_with_every_gate_and_disclosure() -> None:
    approved = evaluate_checkout_preflight(_request())
    assert approved.allowed is True
    assert approved.reason_code == "checkout_preflight_approved"

    denied = evaluate_checkout_preflight(
        _request(gates=_gates(beta_lifetime_discount_enabled=False))
    )
    assert denied.allowed is False
    assert denied.reason_code == "beta_discount_gate_disabled"


def test_founding_rollout_requires_capacity_and_relevant_gate() -> None:
    approved = evaluate_checkout_preflight(
        _request(
            rollout_state=PromotionRolloutState.FOUNDING,
            promotion_type="founding",
            remaining_capacity=1,
        )
    )
    assert approved.allowed is True

    exhausted = evaluate_checkout_preflight(
        _request(
            rollout_state=PromotionRolloutState.FOUNDING,
            promotion_type="founding",
            remaining_capacity=0,
        )
    )
    assert exhausted.reason_code == "founding_capacity_exhausted"


def test_master_authorization_provider_and_account_checks_precede_cohort_opening() -> None:
    cases = [
        (_gates(promotions_enabled=False), "promotion_master_gate_disabled"),
        (_gates(paid_beta_authorized=False), "commercial_authorization_missing"),
        (_gates(provider_ready=False), "payment_provider_not_ready"),
    ]
    for gates, reason in cases:
        decision = evaluate_checkout_preflight(_request(gates=gates))
        assert decision.allowed is False
        assert decision.reason_code == reason

    assert evaluate_checkout_preflight(_request(account_verified=False)).reason_code == "verified_account_required"
    assert evaluate_checkout_preflight(_request(has_active_promotion=True)).reason_code == "promotion_stacking_prohibited"
    assert (
        evaluate_checkout_preflight(_request(disclosure_acknowledged=False)).reason_code
        == "checkout_disclosure_not_acknowledged"
    )


def test_configuration_digest_is_deterministic_and_state_sensitive() -> None:
    gates = _gates()
    first = rollout_configuration_digest(
        rollout_state=PromotionRolloutState.BETA,
        gates=gates,
        extra={"campaign": "beta-2026", "version": 1},
    )
    second = rollout_configuration_digest(
        rollout_state=PromotionRolloutState.BETA,
        gates=gates,
        extra={"version": 1, "campaign": "beta-2026"},
    )
    paused = rollout_configuration_digest(
        rollout_state=PromotionRolloutState.PAUSED,
        gates=gates,
        extra={"campaign": "beta-2026", "version": 1},
    )

    assert first == second
    assert first != paused
    assert len(first) == 64
