from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.session import Base
from app.models.promotion import PromotionAuditRecord, PromotionCampaign, PromotionEligibility
from app.models.sandbox_payment_verification import (
    SandboxPaymentVerificationEvidence,
    SandboxPaymentVerificationRun,
)
from app.models.user import User
from app.services.promotion_entitlements import PromotionConflictError
from app.services.sandbox_payment_verification_persistence import (
    append_verification_evidence,
    complete_verification_run,
    reserve_verification_run,
)


def _db(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'sandbox-verification.db'}")
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)


def _seed_operator(db, *, user_id: int, email: str, account_id: int):
    user = User(id=user_id, email=email, hashed_password="unused", is_active=True, is_superuser=True)
    campaign = PromotionCampaign(
        slug=f"beta-sandbox-{user_id}",
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
        verified_account_id=f"acct-{account_id}",
        eligibility_reason="verified_beta_tester",
    )
    db.add(eligibility)
    db.flush()
    return user, eligibility


def _seed(db):
    return _seed_operator(db, user_id=1, email="operator@example.com", account_id=1)


def test_verification_run_is_idempotent_and_audited(tmp_path: Path) -> None:
    engine, factory = _db(tmp_path)
    now = datetime(2026, 7, 28, 12, 0)
    with factory() as db:
        user, eligibility = _seed(db)
        first = reserve_verification_run(
            db,
            account_id=1,
            eligibility_id=eligibility.id,
            operator_user_id=user.id,
            provider="stripe",
            idempotency_key="verify-1",
            provider_configuration_digest="a" * 64,
            rollout_configuration_digest="b" * 64,
            request_payload={"account_id": 1, "eligibility_id": eligibility.id},
            started_at=now,
        )
        db.commit()
        first_id = first.id
    with factory() as db:
        same = reserve_verification_run(
            db,
            account_id=1,
            eligibility_id=1,
            operator_user_id=1,
            provider="stripe",
            idempotency_key="verify-1",
            provider_configuration_digest="a" * 64,
            rollout_configuration_digest="b" * 64,
            request_payload={"account_id": 1, "eligibility_id": 1},
            started_at=now,
        )
        assert same.id == first_id
        assert db.scalar(select(PromotionAuditRecord)) is not None
    engine.dispose()


def test_same_idempotency_key_is_isolated_between_operators(tmp_path: Path) -> None:
    engine, factory = _db(tmp_path)
    now = datetime(2026, 7, 28, 12, 0)
    with factory() as db:
        first_user, first_eligibility = _seed_operator(
            db,
            user_id=1,
            email="first-operator@example.com",
            account_id=11,
        )
        second_user, second_eligibility = _seed_operator(
            db,
            user_id=2,
            email="second-operator@example.com",
            account_id=22,
        )
        first = reserve_verification_run(
            db,
            account_id=11,
            eligibility_id=first_eligibility.id,
            operator_user_id=first_user.id,
            provider="stripe",
            idempotency_key="shared-key",
            provider_configuration_digest="a" * 64,
            rollout_configuration_digest="b" * 64,
            request_payload={"account_id": 11},
            started_at=now,
        )
        second = reserve_verification_run(
            db,
            account_id=22,
            eligibility_id=second_eligibility.id,
            operator_user_id=second_user.id,
            provider="stripe",
            idempotency_key="shared-key",
            provider_configuration_digest="a" * 64,
            rollout_configuration_digest="b" * 64,
            request_payload={"account_id": 22},
            started_at=now,
        )
        db.commit()

        assert first.id != second.id
        runs = list(db.scalars(select(SandboxPaymentVerificationRun)).all())
        assert {(run.operator_user_id, run.idempotency_key) for run in runs} == {
            (1, "shared-key"),
            (2, "shared-key"),
        }
    engine.dispose()


def test_same_operator_cannot_reuse_key_with_different_data(tmp_path: Path) -> None:
    engine, factory = _db(tmp_path)
    now = datetime(2026, 7, 28, 12, 0)
    with factory() as db:
        user, eligibility = _seed(db)
        reserve_verification_run(
            db,
            account_id=1,
            eligibility_id=eligibility.id,
            operator_user_id=user.id,
            provider="stripe",
            idempotency_key="verify-conflict",
            provider_configuration_digest="a" * 64,
            rollout_configuration_digest="b" * 64,
            request_payload={"account_id": 1},
            started_at=now,
        )
        db.commit()

    with factory() as db:
        with pytest.raises(PromotionConflictError, match="reused with different data"):
            reserve_verification_run(
                db,
                account_id=2,
                eligibility_id=1,
                operator_user_id=1,
                provider="stripe",
                idempotency_key="verify-conflict",
                provider_configuration_digest="a" * 64,
                rollout_configuration_digest="b" * 64,
                request_payload={"account_id": 2},
                started_at=now,
            )
    engine.dispose()


def test_evidence_is_immutable_and_completion_is_digest_bound(tmp_path: Path) -> None:
    engine, factory = _db(tmp_path)
    now = datetime(2026, 7, 28, 12, 0)
    with factory() as db:
        user, eligibility = _seed(db)
        run = reserve_verification_run(
            db,
            account_id=1,
            eligibility_id=eligibility.id,
            operator_user_id=user.id,
            provider="stripe",
            idempotency_key="verify-2",
            provider_configuration_digest="a" * 64,
            rollout_configuration_digest="b" * 64,
            request_payload={"account_id": 1},
            started_at=now,
        )
        evidence = append_verification_evidence(
            db,
            run=run,
            evidence_type="checkout",
            redacted_payload={"session_id": "cs_test_1", "status": "created"},
            recorded_at=now,
        )
        completed = complete_verification_run(
            db,
            run=run,
            evidence_digests=[evidence.evidence_digest],
            checkout_request_id=1,
            completed_at=now,
        )
        assert completed.status == "completed"
        assert len(completed.evidence_digest or "") == 64
        with pytest.raises(PromotionConflictError, match="different content"):
            append_verification_evidence(
                db,
                run=run,
                evidence_type="checkout",
                redacted_payload={"session_id": "cs_test_mutated"},
                recorded_at=now,
            )
        assert db.scalar(select(SandboxPaymentVerificationEvidence)) is not None
    engine.dispose()
