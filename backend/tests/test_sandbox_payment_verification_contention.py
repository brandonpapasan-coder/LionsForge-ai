from contextlib import nullcontext
from datetime import datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.sandbox_payment_verification import SandboxPaymentVerificationRun
from app.services.promotion_entitlements import PromotionConflictError
from app.services.sandbox_payment_verification_persistence import (
    canonical_payload_digest,
    reserve_verification_run,
)


class ContentionSession:
    def __init__(self, winner: SandboxPaymentVerificationRun | None) -> None:
        self.winner = winner
        self.scalar_calls = 0
        self.added: list[object] = []
        self.flush_calls = 0

    def scalar(self, statement):
        self.scalar_calls += 1
        if self.scalar_calls == 1:
            return None
        return self.winner

    def begin_nested(self):
        return nullcontext()

    def add(self, value: object) -> None:
        self.added.append(value)

    def flush(self) -> None:
        self.flush_calls += 1
        raise IntegrityError("insert", {}, RuntimeError("duplicate operator/key"))


def _winner(*, account_id: int = 11, request_payload: dict[str, object] | None = None):
    payload = request_payload or {"account_id": account_id, "eligibility_id": 13}
    started_at = datetime(2026, 7, 28, 14, 0)
    return SandboxPaymentVerificationRun(
        id=41,
        account_id=account_id,
        eligibility_id=13,
        operator_user_id=7,
        provider="stripe",
        idempotency_key="concurrent-key",
        request_digest=canonical_payload_digest(payload),
        provider_configuration_digest="a" * 64,
        rollout_configuration_digest="b" * 64,
        status="pending",
        reason_code="verification_reserved",
        started_at=started_at,
        expires_at=started_at + timedelta(hours=24),
    )


def _reserve(db: ContentionSession, *, account_id: int = 11):
    return reserve_verification_run(
        db,  # type: ignore[arg-type]
        account_id=account_id,
        eligibility_id=13,
        operator_user_id=7,
        provider="stripe",
        idempotency_key="concurrent-key",
        provider_configuration_digest="a" * 64,
        rollout_configuration_digest="b" * 64,
        request_payload={"account_id": account_id, "eligibility_id": 13},
        started_at=datetime(2026, 7, 28, 14, 0),
    )


def test_matching_uniqueness_collision_returns_persisted_winner_without_duplicate_audit() -> None:
    winner = _winner()
    db = ContentionSession(winner)

    resolved = _reserve(db)

    assert resolved is winner
    assert db.scalar_calls == 2
    assert db.flush_calls == 1
    assert len(db.added) == 1
    assert isinstance(db.added[0], SandboxPaymentVerificationRun)


def test_conflicting_uniqueness_collision_fails_closed_without_duplicate_audit() -> None:
    db = ContentionSession(_winner())

    with pytest.raises(PromotionConflictError, match="reused with different data"):
        _reserve(db, account_id=22)

    assert db.scalar_calls == 2
    assert db.flush_calls == 1
    assert len(db.added) == 1


def test_unresolved_uniqueness_collision_raises_domain_conflict() -> None:
    db = ContentionSession(None)

    with pytest.raises(PromotionConflictError, match="contention could not be resolved"):
        _reserve(db)

    assert db.scalar_calls == 2
    assert db.flush_calls == 1
