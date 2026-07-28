from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.session import Base
from app.models.sandbox_payment_verification import (
    SandboxPaymentVerificationEvidence,
    SandboxPaymentVerificationRun,
)
from app.services.promotion_entitlements import PromotionUnavailableError
from app.services.sandbox_payment_verification import SandboxVerificationRequest
from app.services.sandbox_payment_verification_orchestrator import execute_sandbox_payment_verification


def _db(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'sandbox-verification.db'}")
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _request() -> SandboxVerificationRequest:
    return SandboxVerificationRequest(
        operator_user_id=7,
        account_id=11,
        eligibility_id=13,
        provider="stripe",
        provider_configuration_digest=_digest("provider"),
        rollout_configuration_digest=_digest("rollout"),
        checkout_request_digest=_digest("checkout"),
        webhook_event_digest=_digest("webhook"),
        provider_mode="sandbox",
        rollout_state="internal",
        provider_validation_current=True,
        preflight_allowed=True,
        account_verified=True,
        eligibility_reserved=True,
        idempotency_key="verify-1",
        requested_at=datetime(2026, 7, 28, 13, 0),
    )


class Checkout:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls = 0

    def create_session(self, *, idempotency_key: str):
        self.calls += 1
        if self.fail:
            raise RuntimeError("provider unavailable")
        return {"id": "cs_test_123", "status": "created", "secret": "must-not-persist"}


class Webhook:
    def __init__(self, *, event_digest: str, verified: bool = True) -> None:
        self.event_digest = event_digest
        self.verified = verified

    def verify(self, *, provider_session_id: str):
        return {
            "verified": self.verified,
            "event_type": "checkout.session.completed",
            "event_digest": self.event_digest,
            "raw_secret": "must-not-persist",
        }


def test_successful_verification_persists_only_redacted_evidence(tmp_path: Path) -> None:
    engine, factory = _db(tmp_path)
    request = _request()
    checkout = Checkout()
    webhook = Webhook(event_digest=request.webhook_event_digest)
    with factory() as db:
        result = execute_sandbox_payment_verification(
            db,
            request=request,
            checkout_request_id=17,
            checkout_executor=checkout,
            webhook_verifier=webhook,
            now=request.requested_at,
        )
        db.commit()
        assert result.status == "completed"
        assert len(result.evidence_digest) == 64

    with factory() as db:
        run = db.scalar(select(SandboxPaymentVerificationRun))
        evidence = list(db.scalars(select(SandboxPaymentVerificationEvidence)).all())
        assert run is not None and run.checkout_request_id == 17
        assert {item.evidence_type for item in evidence} == {"sandbox_checkout", "synthetic_webhook"}
        serialized = str([item.redacted_payload for item in evidence])
        assert "must-not-persist" not in serialized
    engine.dispose()


def test_provider_failure_rolls_back_new_verification_run(tmp_path: Path) -> None:
    engine, factory = _db(tmp_path)
    request = _request()
    with factory() as db:
        with pytest.raises(RuntimeError, match="provider unavailable"):
            execute_sandbox_payment_verification(
                db,
                request=request,
                checkout_request_id=17,
                checkout_executor=Checkout(fail=True),
                webhook_verifier=Webhook(event_digest=request.webhook_event_digest),
                now=request.requested_at,
            )
        db.rollback()
        assert db.scalar(select(SandboxPaymentVerificationRun)) is None
    engine.dispose()


def test_webhook_digest_mismatch_fails_closed_and_rolls_back(tmp_path: Path) -> None:
    engine, factory = _db(tmp_path)
    request = _request()
    with factory() as db:
        with pytest.raises(PromotionUnavailableError, match="evidence digest mismatch"):
            execute_sandbox_payment_verification(
                db,
                request=request,
                checkout_request_id=17,
                checkout_executor=Checkout(),
                webhook_verifier=Webhook(event_digest=_digest("mutated")),
                now=request.requested_at,
            )
        db.rollback()
        assert db.scalar(select(SandboxPaymentVerificationRun)) is None
        assert db.scalar(select(SandboxPaymentVerificationEvidence)) is None
    engine.dispose()


def test_denied_preflight_never_calls_provider(tmp_path: Path) -> None:
    engine, factory = _db(tmp_path)
    request = _request()
    denied = SandboxVerificationRequest(**{**request.__dict__, "preflight_allowed": False})
    checkout = Checkout()
    with factory() as db:
        with pytest.raises(PromotionUnavailableError, match="promotion_preflight_denied"):
            execute_sandbox_payment_verification(
                db,
                request=denied,
                checkout_request_id=17,
                checkout_executor=checkout,
                webhook_verifier=Webhook(event_digest=denied.webhook_event_digest),
                now=denied.requested_at,
            )
        assert checkout.calls == 0
    engine.dispose()
