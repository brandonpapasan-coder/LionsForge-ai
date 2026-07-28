from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.session import Base
from app.services.sandbox_payment_verification import SandboxVerificationRequest
from app.services.sandbox_payment_verification_orchestrator import execute_sandbox_payment_verification


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
        provider_mode="sandbox",
        rollout_state="internal",
        idempotency_key="stable-retry-1",
        requested_at=datetime(2026, 7, 28, 13, 0),
    )


class Checkout:
    def __init__(self) -> None:
        self.calls = 0

    def create_session(self, *, idempotency_key: str):
        self.calls += 1
        return {"id": "cs_test_stable", "status": "created"}


class Webhook:
    def __init__(self) -> None:
        self.calls = 0

    def verify(self, *, provider_session_id: str):
        self.calls += 1
        return {
            "verified": True,
            "event_type": "checkout.session.completed",
            "event_digest": _digest("stable-webhook"),
        }


def test_completed_retry_accepts_later_server_timestamp_without_adapter_calls(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'stable-retry.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    request = _request()
    checkout = Checkout()
    webhook = Webhook()

    with factory() as db:
        first = execute_sandbox_payment_verification(
            db,
            request=request,
            checkout_request_id=17,
            checkout_executor=checkout,
            webhook_verifier=webhook,
            now=request.requested_at,
        )
        db.commit()

    later_request = replace(request, requested_at=request.requested_at + timedelta(minutes=5))
    with factory() as db:
        replay = execute_sandbox_payment_verification(
            db,
            request=later_request,
            checkout_request_id=17,
            checkout_executor=checkout,
            webhook_verifier=webhook,
            now=later_request.requested_at,
        )

    assert replay.verification_run_id == first.verification_run_id
    assert replay.provider_session_id == first.provider_session_id
    assert replay.evidence_digest == first.evidence_digest
    assert checkout.calls == 1
    assert webhook.calls == 1
    engine.dispose()
