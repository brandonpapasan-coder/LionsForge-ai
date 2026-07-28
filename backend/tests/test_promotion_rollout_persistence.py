from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.session import Base
from app.models.promotion import PromotionCampaign, PromotionEligibility, PromotionRedemption, SubscriptionPriceProtection
from app.models.promotion_rollout import PromotionCheckoutRequest, PromotionProviderEvent
from app.models.user import User
from app.services.promotion_checkout import persist_subscription_lifecycle_event
from app.services.promotion_entitlements import PromotionConflictError, PromotionUnavailableError
from app.services.promotion_rollout import (
    CheckoutPreflightRequest,
    PromotionGateSnapshot,
    PromotionRolloutState,
    evaluate_checkout_preflight,
)
from app.services.promotion_rollout_persistence import (
    authorize_rollout_state,
    ingest_provider_event,
    reserve_checkout_request,
)
from app.services.promotion_rollout_status import read_promotion_rollout_status


def _db(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'rollout.db'}")
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)


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


def _seed_eligibility(session_factory, *, user_id: int = 1) -> int:
    now = datetime(2026, 7, 28, 12, 0)
    with session_factory() as db:
        user = User(
            id=user_id,
            email=f"operator-{user_id}@example.com",
            hashed_password="not-used",
            is_active=True,
            is_superuser=True,
        )
        campaign = PromotionCampaign(
            slug=f"beta-{user_id}",
            promotion_type="beta",
            discount_percent=50,
            active=True,
        )
        db.add_all([user, campaign])
        db.flush()
        eligibility = PromotionEligibility(
            campaign_id=campaign.id,
            user_id=user.id,
            status="reserved",
            verified_account_id=f"acct-{user_id}",
            reserved_until=now + timedelta(minutes=30),
            eligibility_reason="verified_beta_tester",
        )
        db.add(eligibility)
        db.commit()
        return eligibility.id


def test_rollout_authorization_fails_closed_without_commercial_gates(tmp_path: Path) -> None:
    engine, session_factory = _db(tmp_path)
    with session_factory() as db:
        with pytest.raises(PromotionUnavailableError, match="requires all commercial"):
            authorize_rollout_state(
                db,
                rollout_state=PromotionRolloutState.BETA,
                gates=_gates(paid_beta_authorized=False),
                actor_type="operator",
                actor_reference="admin@example.com",
                reason_code="beta_open",
                authorized_at=datetime(2026, 7, 28, 12, 0),
            )
    engine.dispose()


def test_checkout_request_is_idempotent_and_payload_bound(tmp_path: Path) -> None:
    engine, session_factory = _db(tmp_path)
    eligibility_id = _seed_eligibility(session_factory)
    now = datetime(2026, 7, 28, 12, 0)
    with session_factory() as db:
        first = reserve_checkout_request(
            db,
            eligibility_id=eligibility_id,
            provider="stripe",
            idempotency_key="checkout-1",
            request_payload={"price": "price-test", "account": "acct-1"},
            created_at=now,
        )
        db.commit()
        first_id = first.id
    with session_factory() as db:
        same = reserve_checkout_request(
            db,
            eligibility_id=eligibility_id,
            provider="stripe",
            idempotency_key="checkout-1",
            request_payload={"price": "price-test", "account": "acct-1"},
            created_at=now,
        )
        assert same.id == first_id
        with pytest.raises(PromotionConflictError, match="different request data"):
            reserve_checkout_request(
                db,
                eligibility_id=eligibility_id,
                provider="stripe",
                idempotency_key="checkout-1",
                request_payload={"price": "price-other", "account": "acct-1"},
                created_at=now,
            )
    engine.dispose()


def test_provider_event_replay_is_safe_and_mutation_is_rejected(tmp_path: Path) -> None:
    engine, session_factory = _db(tmp_path)
    now = datetime(2026, 7, 28, 12, 0)
    with session_factory() as db:
        record, replay = ingest_provider_event(
            db,
            provider="stripe",
            provider_event_id="evt-1",
            event_type="checkout.session.completed",
            payload={"subscription": "sub-1"},
            signature_verified=True,
            received_at=now,
        )
        db.commit()
        assert replay is False
        record_id = record.id
    with session_factory() as db:
        same, replay = ingest_provider_event(
            db,
            provider="stripe",
            provider_event_id="evt-1",
            event_type="checkout.session.completed",
            payload={"subscription": "sub-1"},
            signature_verified=True,
            received_at=now,
        )
        assert replay is True
        assert same.id == record_id
        with pytest.raises(PromotionConflictError, match="different content"):
            ingest_provider_event(
                db,
                provider="stripe",
                provider_event_id="evt-1",
                event_type="checkout.session.completed",
                payload={"subscription": "sub-mutated"},
                signature_verified=True,
                received_at=now,
            )
    engine.dispose()


def test_invalid_signature_is_not_persisted(tmp_path: Path) -> None:
    engine, session_factory = _db(tmp_path)
    with session_factory() as db:
        with pytest.raises(PromotionUnavailableError, match="signature verification failed"):
            ingest_provider_event(
                db,
                provider="stripe",
                provider_event_id="evt-invalid",
                event_type="checkout.session.completed",
                payload={},
                signature_verified=False,
                received_at=datetime(2026, 7, 28, 12, 0),
            )
        assert db.scalar(select(PromotionProviderEvent)) is None
    engine.dispose()


def test_paused_rollout_blocks_new_checkout_but_lifecycle_still_processes(tmp_path: Path) -> None:
    engine, session_factory = _db(tmp_path)
    eligibility_id = _seed_eligibility(session_factory, user_id=2)
    now = datetime(2026, 7, 28, 12, 0)
    decision = evaluate_checkout_preflight(
        CheckoutPreflightRequest(
            rollout_state=PromotionRolloutState.PAUSED,
            promotion_type="beta",
            is_internal_account=False,
            account_verified=True,
            campaign_active=True,
            has_active_promotion=False,
            disclosure_acknowledged=True,
            remaining_capacity=None,
            gates=_gates(),
        )
    )
    assert decision.allowed is False
    assert decision.reason_code == "rollout_paused"

    with session_factory() as db:
        eligibility = db.get(PromotionEligibility, eligibility_id)
        campaign = db.get(PromotionCampaign, eligibility.campaign_id)
        eligibility.status = "active"
        eligibility.reserved_until = None
        redemption = PromotionRedemption(
            eligibility_id=eligibility.id,
            provider="stripe",
            provider_customer_id="cus-2",
            provider_subscription_id="sub-2",
            internal_entitlement_id="ent-2",
            started_at=now,
            status="active",
        )
        db.add(redemption)
        db.flush()
        protection = SubscriptionPriceProtection(
            redemption_id=redemption.id,
            protection_type="continuous_lifetime",
            protected_percent=50,
            continuous_subscription_required=True,
            grace_period_days=7,
            regular_price_amount_cents=2000,
            regular_price_currency="USD",
            status="active",
        )
        db.add(protection)
        db.commit()
        redemption_id = redemption.id

    with session_factory() as db:
        eligibility = db.get(PromotionEligibility, eligibility_id)
        campaign = db.get(PromotionCampaign, eligibility.campaign_id)
        redemption = db.get(PromotionRedemption, redemption_id)
        protection = db.scalar(select(SubscriptionPriceProtection).where(
            SubscriptionPriceProtection.redemption_id == redemption.id
        ))
        result = persist_subscription_lifecycle_event(
            db,
            campaign=campaign,
            eligibility=eligibility,
            redemption=redemption,
            protection=protection,
            event_type="payment_failed",
            occurred_at=now + timedelta(days=1),
            within_payment_grace=True,
            provider_event_id="evt-payment-failed",
        )
        db.commit()
        assert result.eligibility_status == "grace"
        assert protection.status == "grace"
    engine.dispose()


def test_operator_status_defaults_disabled_and_reports_counts(tmp_path: Path) -> None:
    engine, session_factory = _db(tmp_path)
    eligibility_id = _seed_eligibility(session_factory, user_id=3)
    with session_factory() as db:
        reserve_checkout_request(
            db,
            eligibility_id=eligibility_id,
            provider="stripe",
            idempotency_key="status-checkout",
            request_payload={"account": "acct-3"},
            created_at=datetime(2026, 7, 28, 12, 0),
        )
        ingest_provider_event(
            db,
            provider="stripe",
            provider_event_id="evt-status",
            event_type="unknown.event",
            payload={},
            signature_verified=True,
            received_at=datetime(2026, 7, 28, 12, 0),
        )
        db.commit()

    with session_factory() as db:
        status = read_promotion_rollout_status(db, gates=_gates(provider_ready=False))
        assert status.rollout_state == "disabled"
        assert status.reserved_eligibilities == 1
        assert status.checkout_requests_reserved == 1
        assert status.provider_events_rejected == 1
        assert status.gates["provider_ready"] is False
    engine.dispose()
