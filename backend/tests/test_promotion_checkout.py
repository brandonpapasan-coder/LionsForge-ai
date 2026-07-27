from datetime import datetime, timezone

import pytest

from app.models.promotion import PromotionCampaign
from app.services.promotion_checkout import build_checkout_disclosure
from app.services.promotion_entitlements import PromotionUnavailableError


def test_founding_checkout_discloses_regular_renewal_amount_and_date() -> None:
    campaign = PromotionCampaign(
        id=1,
        slug="founding-2026",
        promotion_type="founding",
        discount_percent=50,
        duration_months=12,
        capacity=20_000,
        active=True,
    )
    transition = datetime(2027, 8, 1, tzinfo=timezone.utc)

    disclosure = build_checkout_disclosure(
        campaign=campaign,
        regular_price_amount_cents=2999,
        currency="usd",
        regular_price_effective_at=transition,
    )

    assert disclosure.discounted_price_amount_cents == 1499
    assert disclosure.regular_price_amount_cents == 2999
    assert disclosure.currency == "USD"
    assert disclosure.promotional_period_months == 12
    assert disclosure.regular_price_effective_at == transition
    assert "2027-08-01" in disclosure.disclosure_text
    assert "USD 29.99" in disclosure.disclosure_text


def test_founding_checkout_fails_closed_without_transition_date() -> None:
    campaign = PromotionCampaign(
        id=1,
        slug="founding-2026",
        promotion_type="founding",
        discount_percent=50,
        duration_months=12,
        capacity=20_000,
        active=True,
    )

    with pytest.raises(PromotionUnavailableError, match="twelve-month transition date"):
        build_checkout_disclosure(
            campaign=campaign,
            regular_price_amount_cents=2999,
            currency="USD",
            regular_price_effective_at=None,
        )


def test_founding_checkout_rejects_wrong_promotion_duration() -> None:
    campaign = PromotionCampaign(
        id=1,
        slug="founding-2026",
        promotion_type="founding",
        discount_percent=50,
        duration_months=6,
        capacity=20_000,
        active=True,
    )

    with pytest.raises(PromotionUnavailableError, match="twelve-month transition date"):
        build_checkout_disclosure(
            campaign=campaign,
            regular_price_amount_cents=2999,
            currency="USD",
            regular_price_effective_at=datetime(2027, 8, 1, tzinfo=timezone.utc),
        )


def test_beta_checkout_discloses_continuous_subscription_requirement() -> None:
    campaign = PromotionCampaign(
        id=2,
        slug="beta-lifetime",
        promotion_type="beta",
        discount_percent=50,
        duration_months=None,
        capacity=None,
        active=True,
    )

    disclosure = build_checkout_disclosure(
        campaign=campaign,
        regular_price_amount_cents=2999,
        currency="USD",
        regular_price_effective_at=None,
    )

    assert disclosure.discounted_price_amount_cents == 1499
    assert disclosure.promotional_period_months is None
    assert "continuously active" in disclosure.disclosure_text
    assert "failed-payment grace policy" in disclosure.disclosure_text


def test_checkout_rejects_invalid_regular_price_or_currency() -> None:
    campaign = PromotionCampaign(
        id=2,
        slug="beta-lifetime",
        promotion_type="beta",
        discount_percent=50,
        duration_months=None,
        capacity=None,
        active=True,
    )

    with pytest.raises(ValueError, match="regular price"):
        build_checkout_disclosure(
            campaign=campaign,
            regular_price_amount_cents=0,
            currency="USD",
            regular_price_effective_at=None,
        )
    with pytest.raises(ValueError, match="three-letter"):
        build_checkout_disclosure(
            campaign=campaign,
            regular_price_amount_cents=2999,
            currency="US",
            regular_price_effective_at=None,
        )
