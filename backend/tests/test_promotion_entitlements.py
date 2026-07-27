from datetime import datetime, timezone

import pytest

from app.core.config import Settings
from app.services.promotion_entitlements import (
    FOUNDING_CAPACITY,
    decide_lifecycle_transition,
    payment_provider_metadata,
)


def test_all_commercial_promotion_flags_default_fail_closed() -> None:
    settings = Settings(_env_file=None)

    assert settings.promotions_enabled is False
    assert settings.beta_lifetime_discount_enabled is False
    assert settings.founding_subscriber_enrollment_enabled is False
    assert settings.paid_beta_authorized is False
    assert settings.public_beta_promotion_enabled() is False
    assert settings.public_founding_promotion_enabled() is False


@pytest.mark.parametrize(
    ("overrides", "beta_enabled", "founding_enabled"),
    [
        ({"promotions_enabled": True}, False, False),
        ({"promotions_enabled": True, "paid_beta_authorized": True}, False, False),
        (
            {
                "promotions_enabled": True,
                "paid_beta_authorized": True,
                "beta_lifetime_discount_enabled": True,
            },
            True,
            False,
        ),
        (
            {
                "promotions_enabled": True,
                "paid_beta_authorized": True,
                "founding_subscriber_enrollment_enabled": True,
            },
            False,
            True,
        ),
    ],
)
def test_relevant_flag_and_paid_authorization_are_both_required(
    overrides: dict[str, bool], beta_enabled: bool, founding_enabled: bool
) -> None:
    settings = Settings(_env_file=None, **overrides)

    assert settings.public_beta_promotion_enabled() is beta_enabled
    assert settings.public_founding_promotion_enabled() is founding_enabled


def test_founding_capacity_is_exactly_twenty_thousand() -> None:
    assert FOUNDING_CAPACITY == 20_000


def test_failed_payment_enters_grace_without_losing_continuity() -> None:
    decision = decide_lifecycle_transition(
        event_type="payment_failed",
        promotion_type="beta",
        continuous_subscription_required=True,
        within_payment_grace=True,
    )

    assert decision.eligibility_status == "grace"
    assert decision.protection_status == "grace"
    assert decision.release_founding_position is False


def test_beta_reactivation_after_lapse_does_not_restore_lifetime_discount() -> None:
    decision = decide_lifecycle_transition(
        event_type="reactivated",
        promotion_type="beta",
        continuous_subscription_required=True,
    )

    assert decision.eligibility_status == "ineligible"
    assert decision.protection_status == "ended"
    assert decision.reason_code == "continuous_subscription_broken"


def test_founding_cancellation_releases_unconsumed_position_policy() -> None:
    decision = decide_lifecycle_transition(
        event_type="canceled",
        promotion_type="founding",
        continuous_subscription_required=False,
    )

    assert decision.eligibility_status == "ended"
    assert decision.release_founding_position is True


def test_chargeback_ends_entitlement_deterministically() -> None:
    decision = decide_lifecycle_transition(
        event_type="chargeback",
        promotion_type="beta",
        continuous_subscription_required=True,
    )

    assert decision.eligibility_status == "ended"
    assert decision.protection_status == "ended"
    assert decision.reason_code == "subscription_chargeback"


def test_provider_metadata_binds_discount_to_internal_entitlement() -> None:
    metadata = payment_provider_metadata(
        eligibility_id=42,
        campaign_slug="founding-2026",
        entitlement_id="ent_abc123",
    )

    assert metadata == {
        "onyxmane_promotion_eligibility_id": "42",
        "onyxmane_promotion_campaign": "founding-2026",
        "onyxmane_internal_entitlement_id": "ent_abc123",
    }


def test_unknown_lifecycle_event_fails_closed() -> None:
    with pytest.raises(ValueError, match="unsupported promotion lifecycle event"):
        decide_lifecycle_transition(
            event_type="provider_unknown",
            promotion_type="beta",
            continuous_subscription_required=True,
        )
