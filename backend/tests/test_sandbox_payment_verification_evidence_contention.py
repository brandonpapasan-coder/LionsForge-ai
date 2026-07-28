from contextlib import nullcontext
from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.sandbox_payment_verification import (
    SandboxPaymentVerificationEvidence,
    SandboxPaymentVerificationRun,
)
from app.services.promotion_entitlements import PromotionConflictError
from app.services.sandbox_payment_verification_persistence import (
    append_verification_evidence,
    canonical_payload_digest,
)


class EvidenceContentionSession:
    def __init__(self, winner: SandboxPaymentVerificationEvidence | None) -> None:
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
        raise IntegrityError("insert", {}, RuntimeError("duplicate run/evidence type"))


def _run() -> SandboxPaymentVerificationRun:
    return SandboxPaymentVerificationRun(id=41)


def _winner(*, payload: dict[str, object] | None = None) -> SandboxPaymentVerificationEvidence:
    redacted_payload = payload or {"session_id": "cs_test_1", "status": "created"}
    return SandboxPaymentVerificationEvidence(
        id=51,
        verification_run_id=41,
        evidence_type="checkout",
        evidence_digest=canonical_payload_digest(redacted_payload),
        redacted_payload=redacted_payload,
        recorded_at=datetime(2026, 7, 28, 14, 0),
    )


def _append(db: EvidenceContentionSession, *, payload: dict[str, object] | None = None):
    return append_verification_evidence(
        db,  # type: ignore[arg-type]
        run=_run(),
        evidence_type="checkout",
        redacted_payload=payload or {"session_id": "cs_test_1", "status": "created"},
        recorded_at=datetime(2026, 7, 28, 14, 0),
    )


def test_matching_evidence_collision_returns_persisted_winner() -> None:
    winner = _winner()
    db = EvidenceContentionSession(winner)

    resolved = _append(db)

    assert resolved is winner
    assert db.scalar_calls == 2
    assert db.flush_calls == 1
    assert len(db.added) == 1
    assert isinstance(db.added[0], SandboxPaymentVerificationEvidence)


def test_conflicting_evidence_collision_fails_closed() -> None:
    db = EvidenceContentionSession(_winner())

    with pytest.raises(PromotionConflictError, match="different content"):
        _append(db, payload={"session_id": "cs_test_mutated", "status": "created"})

    assert db.scalar_calls == 2
    assert db.flush_calls == 1
    assert len(db.added) == 1


def test_unresolved_evidence_collision_raises_domain_conflict() -> None:
    db = EvidenceContentionSession(None)

    with pytest.raises(PromotionConflictError, match="contention could not be resolved"):
        _append(db)

    assert db.scalar_calls == 2
    assert db.flush_calls == 1
