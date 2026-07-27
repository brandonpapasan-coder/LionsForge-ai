from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401 - register all mapped tables
from app.db.session import Base
from app.models.promotion import (
    FoundingSubscriberSequence,
    PromotionAuditRecord,
    PromotionCampaign,
    PromotionEligibility,
    PromotionRedemption,
    SubscriptionPriceProtection,
)
from app.services.promotion_checkout import (
    activate_reserved_promotion,
    persist_subscription_lifecycle_event,
)
from app.services.promotion_entitlements import (
    PromotionConflictError,
    PromotionUnavailableError,
    release_abandoned_reservations,
    reserve_founding_position,
)


def _database(tmp_path: Path):
    database_path = tmp_path / "promotion-contention.db"
    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)


def _create_campaign(session_factory, *, capacity: int, promotion_type: str = "founding") -> int:
    with session_factory() as db:
        campaign = PromotionCampaign(
            slug=f"{promotion_type}-capacity-{capacity}",
            promotion_type=promotion_type,
            discount_percent=50,
            duration_months=12 if promotion_type == "founding" else None,
            capacity=capacity if promotion_type == "founding" else None,
            active=True,
        )
        db.add(campaign)
        db.commit()
        return campaign.id


def test_abandoned_checkout_releases_and_reuses_same_position(tmp_path: Path) -> None:
    engine, session_factory = _database(tmp_path)
    campaign_id = _create_campaign(session_factory, capacity=1)
    reserved_at = datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc).replace(tzinfo=None)

    with session_factory() as db:
        campaign = db.get(PromotionCampaign, campaign_id)
        first_eligibility, first_sequence = reserve_founding_position(
            db,
            campaign=campaign,
            user_id=101,
            verified_account_id="acct-first",
            now=reserved_at,
        )
        first_position = first_sequence.position
        first_eligibility.reserved_until = reserved_at - timedelta(seconds=1)
        db.commit()

    with session_factory() as db:
        assert release_abandoned_reservations(db, now=reserved_at) == 1
        db.commit()

    with session_factory() as db:
        campaign = db.get(PromotionCampaign, campaign_id)
        second_eligibility, second_sequence = reserve_founding_position(
            db,
            campaign=campaign,
            user_id=102,
            verified_account_id="acct-second",
            now=reserved_at,
        )
        db.commit()

        assert first_position == 1
        assert second_sequence.position == 1
        assert second_sequence.eligibility_id == second_eligibility.id
        assert second_sequence.allocation_status == "reserved"
        assert db.scalar(select(PromotionAuditRecord).where(
            PromotionAuditRecord.event_type == "checkout_reservation_expired"
        )) is not None

    engine.dispose()


def test_consumed_position_is_never_reissued(tmp_path: Path) -> None:
    engine, session_factory = _database(tmp_path)
    campaign_id = _create_campaign(session_factory, capacity=1)
    now = datetime(2026, 7, 27, 12, 0)

    with session_factory() as db:
        campaign = db.get(PromotionCampaign, campaign_id)
        eligibility, sequence = reserve_founding_position(
            db,
            campaign=campaign,
            user_id=201,
            verified_account_id="acct-consumed",
            now=now,
        )
        eligibility.status = "active"
        eligibility.reserved_until = None
        sequence.allocation_status = "consumed"
        db.commit()

    with session_factory() as db:
        campaign = db.get(PromotionCampaign, campaign_id)
        with pytest.raises(PromotionUnavailableError, match="allocation is exhausted"):
            reserve_founding_position(
                db,
                campaign=campaign,
                user_id=202,
                verified_account_id="acct-too-late",
                now=now,
            )

        positions = db.scalars(select(FoundingSubscriberSequence.position)).all()
        assert positions == [1]

    engine.dispose()


def test_simultaneous_checkout_cannot_oversubscribe_capacity(tmp_path: Path) -> None:
    engine, session_factory = _database(tmp_path)
    campaign_id = _create_campaign(session_factory, capacity=2)
    now = datetime(2026, 7, 27, 12, 0)

    def attempt(user_id: int) -> str:
        with session_factory() as db:
            campaign = db.get(PromotionCampaign, campaign_id)
            try:
                reserve_founding_position(
                    db,
                    campaign=campaign,
                    user_id=user_id,
                    verified_account_id=f"acct-{user_id}",
                    now=now,
                )
                db.commit()
                return "qualified"
            except PromotionUnavailableError:
                db.rollback()
                return "regular_price"

    with ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(attempt, range(300, 306)))

    with session_factory() as db:
        active_allocations = db.scalars(
            select(FoundingSubscriberSequence).where(
                FoundingSubscriberSequence.allocation_status == "reserved"
            )
        ).all()
        positions = sorted(sequence.position for sequence in active_allocations)

    assert results.count("qualified") == 2
    assert results.count("regular_price") == 4
    assert positions == [1, 2]

    engine.dispose()


def _activate_beta(session_factory, campaign_id: int, *, user_id: int, subscription_id: str):
    now = datetime(2026, 7, 27, 12, 0)
    with session_factory() as db:
        campaign = db.get(PromotionCampaign, campaign_id)
        eligibility = PromotionEligibility(
            campaign_id=campaign.id,
            user_id=user_id,
            status="reserved",
            verified_account_id=f"acct-{user_id}",
            reserved_until=now + timedelta(minutes=30),
            eligibility_reason="verified_beta_tester",
        )
        db.add(eligibility)
        db.flush()
        result = activate_reserved_promotion(
            db,
            campaign=campaign,
            eligibility=eligibility,
            provider="stripe",
            provider_customer_id=f"cus-{user_id}",
            provider_subscription_id=subscription_id,
            provider_discount_id=f"disc-{user_id}",
            regular_price_amount_cents=2000,
            currency="USD",
            activated_at=now,
            regular_price_effective_at=None,
        )
        db.commit()
        return eligibility.id, result.redemption_id


def test_refund_and_chargeback_persist_deterministic_entitlement_state(tmp_path: Path) -> None:
    engine, session_factory = _database(tmp_path)
    campaign_id = _create_campaign(session_factory, capacity=1, promotion_type="beta")
    eligibility_id, redemption_id = _activate_beta(
        session_factory, campaign_id, user_id=401, subscription_id="sub-lifecycle"
    )

    with session_factory() as db:
        campaign = db.get(PromotionCampaign, campaign_id)
        eligibility = db.get(PromotionEligibility, eligibility_id)
        redemption = db.get(PromotionRedemption, redemption_id)
        protection = db.scalar(select(SubscriptionPriceProtection).where(
            SubscriptionPriceProtection.redemption_id == redemption.id
        ))
        refund = persist_subscription_lifecycle_event(
            db,
            campaign=campaign,
            eligibility=eligibility,
            redemption=redemption,
            protection=protection,
            event_type="refund",
            occurred_at=datetime(2026, 7, 28, 12, 0),
            provider_event_id="evt-refund",
        )
        db.commit()
        assert refund.eligibility_status == "review"
        assert redemption.status == "review"
        assert protection.status == "suspended"
        assert redemption.ended_at is None

    with session_factory() as db:
        campaign = db.get(PromotionCampaign, campaign_id)
        eligibility = db.get(PromotionEligibility, eligibility_id)
        redemption = db.get(PromotionRedemption, redemption_id)
        protection = db.scalar(select(SubscriptionPriceProtection).where(
            SubscriptionPriceProtection.redemption_id == redemption.id
        ))
        chargeback = persist_subscription_lifecycle_event(
            db,
            campaign=campaign,
            eligibility=eligibility,
            redemption=redemption,
            protection=protection,
            event_type="chargeback",
            occurred_at=datetime(2026, 7, 29, 12, 0),
            provider_event_id="evt-chargeback",
        )
        db.commit()
        assert chargeback.eligibility_status == "ended"
        assert redemption.status == "ended"
        assert protection.status == "ended"
        assert redemption.ended_at == datetime(2026, 7, 29, 12, 0)
        events = db.scalars(select(PromotionAuditRecord.event_type).order_by(PromotionAuditRecord.id)).all()
        assert "promotion_refund" in events
        assert "promotion_chargeback" in events

    engine.dispose()


def test_provider_subscription_conflict_leaves_reservation_unmodified(tmp_path: Path) -> None:
    engine, session_factory = _database(tmp_path)
    campaign_id = _create_campaign(session_factory, capacity=1, promotion_type="beta")
    _activate_beta(session_factory, campaign_id, user_id=501, subscription_id="sub-duplicate")
    now = datetime(2026, 7, 27, 13, 0)

    with session_factory() as db:
        campaign = db.get(PromotionCampaign, campaign_id)
        eligibility = PromotionEligibility(
            campaign_id=campaign.id,
            user_id=502,
            status="reserved",
            verified_account_id="acct-502",
            reserved_until=now + timedelta(minutes=30),
            eligibility_reason="verified_beta_tester",
        )
        db.add(eligibility)
        db.commit()
        eligibility_id = eligibility.id

    with session_factory() as db:
        campaign = db.get(PromotionCampaign, campaign_id)
        eligibility = db.get(PromotionEligibility, eligibility_id)
        with pytest.raises(PromotionConflictError, match="already has a promotion redemption"):
            activate_reserved_promotion(
                db,
                campaign=campaign,
                eligibility=eligibility,
                provider="stripe",
                provider_customer_id="cus-502",
                provider_subscription_id="sub-duplicate",
                provider_discount_id="disc-502",
                regular_price_amount_cents=2000,
                currency="USD",
                activated_at=now,
                regular_price_effective_at=None,
            )
        db.commit()

    with session_factory() as db:
        eligibility = db.get(PromotionEligibility, eligibility_id)
        assert eligibility.status == "reserved"
        assert eligibility.reserved_until is not None
        assert db.scalar(select(PromotionRedemption).where(
            PromotionRedemption.eligibility_id == eligibility_id
        )) is None
        assert db.scalar(select(SubscriptionPriceProtection).join(
            PromotionRedemption,
            SubscriptionPriceProtection.redemption_id == PromotionRedemption.id,
        ).where(PromotionRedemption.eligibility_id == eligibility_id)) is None

    engine.dispose()
