from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.session import Base
from app.models.payment_provider import PaymentProviderValidation
from app.models.promotion import PromotionEligibility
from app.models.promotion_rollout import PromotionCheckoutRequest, PromotionRolloutAuthorization
from app.services.promotion_entitlements import PromotionUnavailableError
from app.services.sandbox_payment_verification_readiness import derive_sandbox_verification_request


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _db(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'sandbox-readiness.db'}")
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)


def _seed(db, *, now: datetime) -> None:
    eligibility = PromotionEligibility(
        id=13,
        campaign_id=1,
        user_id=7,
        status="reserved",
        verified_account_id="11",
        reserved_until=now + timedelta(hours=1),
        eligibility_reason="beta_tester",
        created_at=now,
    )
    checkout = PromotionCheckoutRequest(
        id=17,
        eligibility_id=13,
        provider="stripe",
        idempotency_key="checkout-17",
        request_digest=_digest("checkout"),
        status="reserved",
        created_at=now,
    )
    provider = PaymentProviderValidation(
        id=19,
        provider="stripe",
        mode="sandbox",
        configuration_digest=_digest("provider"),
        validation_status="validated",
        reason_code="sandbox_validated",
        validated_at=now - timedelta(minutes=5),
        expires_at=now + timedelta(hours=1),
        api_reference_present=True,
        webhook_reference_present=True,
        price_references_present=True,
        details={},
    )
    rollout = PromotionRolloutAuthorization(
        id=23,
        rollout_state="internal",
        actor_type="operator",
        actor_reference="7",
        reason_code="sandbox_internal",
        configuration_digest=_digest("rollout"),
        authorized_at=now - timedelta(minutes=2),
    )
    db.add_all([eligibility, checkout, provider, rollout])
    db.commit()


def test_derives_request_only_from_authoritative_records(tmp_path: Path) -> None:
    now = datetime(2026, 7, 28, 16, 0)
    engine, factory = _db(tmp_path)
    with factory() as db:
        _seed(db, now=now)
        request = derive_sandbox_verification_request(
            db,
            operator_user_id=7,
            account_id=11,
            eligibility_id=13,
            checkout_request_id=17,
            idempotency_key="verify-17",
            requested_at=now,
        )
        assert request.provider == "stripe"
        assert request.provider_mode == "sandbox"
        assert request.rollout_state == "internal"
        assert request.provider_configuration_digest == _digest("provider")
        assert request.rollout_configuration_digest == _digest("rollout")
        assert request.checkout_request_digest == _digest("checkout")
    engine.dispose()


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("account", "account does not match eligibility"),
        ("expired_eligibility", "eligibility reservation expired"),
        ("checkout_status", "checkout is not reserved"),
        ("provider_expired", "provider validation expired"),
        ("provider_live", "sandbox provider mode is required"),
        ("rollout_external", "internal sandbox rollout authorization is required"),
    ],
)
def test_mismatched_or_stale_state_fails_closed(tmp_path: Path, mutation: str, message: str) -> None:
    now = datetime(2026, 7, 28, 16, 0)
    engine, factory = _db(tmp_path)
    with factory() as db:
        _seed(db, now=now)
        eligibility = db.get(PromotionEligibility, 13)
        checkout = db.get(PromotionCheckoutRequest, 17)
        provider = db.get(PaymentProviderValidation, 19)
        rollout = db.get(PromotionRolloutAuthorization, 23)
        account_id = 11
        if mutation == "account":
            account_id = 12
        elif mutation == "expired_eligibility":
            eligibility.reserved_until = now
        elif mutation == "checkout_status":
            checkout.status = "completed"
        elif mutation == "provider_expired":
            provider.expires_at = now
        elif mutation == "provider_live":
            provider.mode = "live"
        elif mutation == "rollout_external":
            rollout.rollout_state = "disabled"
        db.commit()

        with pytest.raises(PromotionUnavailableError, match=message):
            derive_sandbox_verification_request(
                db,
                operator_user_id=7,
                account_id=account_id,
                eligibility_id=13,
                checkout_request_id=17,
                idempotency_key="verify-17",
                requested_at=now,
            )
    engine.dispose()
