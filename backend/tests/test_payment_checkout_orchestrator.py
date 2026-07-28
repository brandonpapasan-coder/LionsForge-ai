from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.session import Base
from app.models.promotion import PromotionCampaign, PromotionEligibility
from app.models.promotion_rollout import PromotionCheckoutRequest
from app.models.user import User
from app.services.payment_checkout_orchestrator import orchestrate_internal_checkout
from app.services.payment_provider_readiness import (
    InternalCheckoutRequest,
    ProviderMode,
    ProviderReadinessDecision,
    ProviderReferenceSet,
    provider_configuration_digest,
)
from app.services.promotion_entitlements import PromotionConflictError, PromotionUnavailableError
from app.services.promotion_rollout import CheckoutPreflightDecision


def _db(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'checkout-orchestrator.db'}")
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)


def _seed(session_factory) -> int:
    with session_factory() as db:
        user = User(id=1, email="internal@example.com", hashed_password="unused", is_active=True, is_superuser=True)
        campaign = PromotionCampaign(slug="internal-beta", promotion_type="beta", discount_percent=50, active=True)
        db.add_all([user, campaign])
        db.flush()
        eligibility = PromotionEligibility(
            campaign_id=campaign.id,
            user_id=user.id,
            status="reserved",
            verified_account_id="acct-1",
            eligibility_reason="verified_beta_tester",
        )
        db.add(eligibility)
        db.commit()
        return eligibility.id


def _references() -> ProviderReferenceSet:
    base = ProviderReferenceSet(
        provider="stripe",
        mode=ProviderMode.SANDBOX,
        api_credential_reference="secret://stripe/test/api",
        webhook_secret_reference="secret://stripe/test/webhook",
        beta_price_reference="price_test_beta",
        founding_price_reference="price_test_founding",
        currency="USD",
        account_mode=ProviderMode.SANDBOX,
        validated_at=datetime(2026, 7, 28, 12, 0),
        validation_digest=None,
    )
    return ProviderReferenceSet(**{**base.__dict__, "validation_digest": provider_configuration_digest(base)})


def _request(eligibility_id: int) -> InternalCheckoutRequest:
    return InternalCheckoutRequest(
        account_id=1,
        eligibility_id=eligibility_id,
        promotion_type="beta",
        idempotency_key="checkout-key-1",
        amount_minor=1000,
        currency="USD",
        success_url="https://example.com/success",
        cancel_url="https://example.com/cancel",
        metadata={"account_id": "1", "eligibility_id": str(eligibility_id)},
    )


class Adapter:
    def __init__(self, *, session_id: str = "cs_test_1", fail: bool = False):
        self.session_id = session_id
        self.fail = fail
        self.calls = 0

    def create_checkout_session(self, *, credential_reference, request):
        self.calls += 1
        assert credential_reference.startswith("secret://")
        if self.fail:
            raise RuntimeError("provider unavailable")
        return {
            "id": self.session_id,
            "url": "https://checkout.example.test/session",
            "status": "open",
            "client_secret": "must-not-persist",
        }


def _approved(digest: str) -> CheckoutPreflightDecision:
    return CheckoutPreflightDecision(True, "checkout_preflight_approved", digest)


def _ready(references: ProviderReferenceSet) -> ProviderReadinessDecision:
    return ProviderReadinessDecision(True, "provider_ready", provider_configuration_digest(references))


def test_orchestrator_persists_only_sanitized_session_binding(tmp_path: Path) -> None:
    engine, session_factory = _db(tmp_path)
    eligibility_id = _seed(session_factory)
    references = _references()
    adapter = Adapter()
    with session_factory() as db:
        result = orchestrate_internal_checkout(
            db,
            preflight=_approved("preflight-digest"),
            references=references,
            readiness=_ready(references),
            request=_request(eligibility_id),
            adapter=adapter,
            created_at=datetime(2026, 7, 28, 12, 0),
        )
        db.commit()
        stored = db.get(PromotionCheckoutRequest, result.checkout_request_id)
        assert stored.status == "completed"
        assert stored.provider_session_id == "cs_test_1"
        assert not hasattr(stored, "client_secret")
        assert result.checkout_url.startswith("https://")
    engine.dispose()


def test_provider_failure_rolls_back_new_reservation(tmp_path: Path) -> None:
    engine, session_factory = _db(tmp_path)
    eligibility_id = _seed(session_factory)
    references = _references()
    with session_factory() as db:
        with pytest.raises(RuntimeError, match="provider unavailable"):
            orchestrate_internal_checkout(
                db,
                preflight=_approved("preflight-digest"),
                references=references,
                readiness=_ready(references),
                request=_request(eligibility_id),
                adapter=Adapter(fail=True),
                created_at=datetime(2026, 7, 28, 12, 0),
            )
        assert db.scalar(select(PromotionCheckoutRequest)) is None
    engine.dispose()


def test_retry_is_payload_bound_and_provider_session_stable(tmp_path: Path) -> None:
    engine, session_factory = _db(tmp_path)
    eligibility_id = _seed(session_factory)
    references = _references()
    with session_factory() as db:
        orchestrate_internal_checkout(
            db,
            preflight=_approved("preflight-digest"),
            references=references,
            readiness=_ready(references),
            request=_request(eligibility_id),
            adapter=Adapter(session_id="cs_test_1"),
            created_at=datetime(2026, 7, 28, 12, 0),
        )
        db.commit()
    with session_factory() as db:
        replay = orchestrate_internal_checkout(
            db,
            preflight=_approved("preflight-digest"),
            references=references,
            readiness=_ready(references),
            request=_request(eligibility_id),
            adapter=Adapter(session_id="cs_test_1"),
            created_at=datetime(2026, 7, 28, 12, 1),
        )
        assert replay.replayed_reservation is True
        with pytest.raises(PromotionConflictError, match="different provider session"):
            orchestrate_internal_checkout(
                db,
                preflight=_approved("preflight-digest"),
                references=references,
                readiness=_ready(references),
                request=_request(eligibility_id),
                adapter=Adapter(session_id="cs_test_other"),
                created_at=datetime(2026, 7, 28, 12, 2),
            )
    engine.dispose()


def test_preflight_and_account_binding_fail_closed_before_provider_call(tmp_path: Path) -> None:
    engine, session_factory = _db(tmp_path)
    eligibility_id = _seed(session_factory)
    references = _references()
    adapter = Adapter()
    with session_factory() as db:
        with pytest.raises(PromotionUnavailableError, match="preflight denied"):
            orchestrate_internal_checkout(
                db,
                preflight=CheckoutPreflightDecision(False, "rollout_paused", "digest"),
                references=references,
                readiness=_ready(references),
                request=_request(eligibility_id),
                adapter=adapter,
                created_at=datetime(2026, 7, 28, 12, 0),
            )
        bad = InternalCheckoutRequest(**{**_request(eligibility_id).__dict__, "metadata": {"account_id": "2", "eligibility_id": str(eligibility_id)}})
        with pytest.raises(PromotionConflictError, match="account binding mismatch"):
            orchestrate_internal_checkout(
                db,
                preflight=_approved("digest"),
                references=references,
                readiness=_ready(references),
                request=bad,
                adapter=adapter,
                created_at=datetime(2026, 7, 28, 12, 0),
            )
        assert adapter.calls == 0
    engine.dispose()
