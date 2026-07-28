from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping


class PromotionRolloutState(StrEnum):
    DISABLED = "disabled"
    INTERNAL = "internal"
    BETA = "beta"
    FOUNDING = "founding"
    PAUSED = "paused"


@dataclass(frozen=True)
class PromotionGateSnapshot:
    promotions_enabled: bool
    paid_beta_authorized: bool
    beta_lifetime_discount_enabled: bool
    founding_subscriber_enrollment_enabled: bool
    provider_ready: bool


@dataclass(frozen=True)
class CheckoutPreflightRequest:
    rollout_state: PromotionRolloutState
    promotion_type: str
    is_internal_account: bool
    account_verified: bool
    campaign_active: bool
    has_active_promotion: bool
    disclosure_acknowledged: bool
    remaining_capacity: int | None
    gates: PromotionGateSnapshot


@dataclass(frozen=True)
class CheckoutPreflightDecision:
    allowed: bool
    reason_code: str
    configuration_digest: str


def rollout_configuration_digest(
    *,
    rollout_state: PromotionRolloutState,
    gates: PromotionGateSnapshot,
    extra: Mapping[str, object] | None = None,
) -> str:
    payload = {
        "rollout_state": rollout_state.value,
        "gates": {
            "promotions_enabled": gates.promotions_enabled,
            "paid_beta_authorized": gates.paid_beta_authorized,
            "beta_lifetime_discount_enabled": gates.beta_lifetime_discount_enabled,
            "founding_subscriber_enrollment_enabled": gates.founding_subscriber_enrollment_enabled,
            "provider_ready": gates.provider_ready,
        },
        "extra": dict(sorted((extra or {}).items())),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def evaluate_checkout_preflight(request: CheckoutPreflightRequest) -> CheckoutPreflightDecision:
    digest = rollout_configuration_digest(
        rollout_state=request.rollout_state,
        gates=request.gates,
        extra={"promotion_type": request.promotion_type},
    )

    def deny(reason_code: str) -> CheckoutPreflightDecision:
        return CheckoutPreflightDecision(False, reason_code, digest)

    if request.rollout_state == PromotionRolloutState.DISABLED:
        return deny("rollout_disabled")
    if request.rollout_state == PromotionRolloutState.PAUSED:
        return deny("rollout_paused")
    if not request.gates.promotions_enabled:
        return deny("promotion_master_gate_disabled")
    if not request.gates.paid_beta_authorized:
        return deny("commercial_authorization_missing")
    if not request.gates.provider_ready:
        return deny("payment_provider_not_ready")
    if not request.account_verified:
        return deny("verified_account_required")
    if not request.campaign_active:
        return deny("campaign_inactive")
    if request.has_active_promotion:
        return deny("promotion_stacking_prohibited")
    if not request.disclosure_acknowledged:
        return deny("checkout_disclosure_not_acknowledged")

    if request.rollout_state == PromotionRolloutState.INTERNAL and not request.is_internal_account:
        return deny("internal_account_required")

    if request.promotion_type == "beta":
        if request.rollout_state not in {PromotionRolloutState.INTERNAL, PromotionRolloutState.BETA}:
            return deny("beta_cohort_not_open")
        if not request.gates.beta_lifetime_discount_enabled:
            return deny("beta_discount_gate_disabled")
    elif request.promotion_type == "founding":
        if request.rollout_state not in {PromotionRolloutState.INTERNAL, PromotionRolloutState.FOUNDING}:
            return deny("founding_cohort_not_open")
        if not request.gates.founding_subscriber_enrollment_enabled:
            return deny("founding_enrollment_gate_disabled")
        if request.remaining_capacity is None or request.remaining_capacity <= 0:
            return deny("founding_capacity_exhausted")
    else:
        return deny("unsupported_promotion_type")

    return CheckoutPreflightDecision(True, "checkout_preflight_approved", digest)
