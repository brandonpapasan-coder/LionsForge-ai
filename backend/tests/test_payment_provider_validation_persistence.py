from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.db.session import Base
from app.models.payment_provider import PaymentProviderValidation
from app.models.promotion import PromotionAuditRecord
from app.services.payment_provider_readiness import (
    ProviderMode,
    ProviderReadinessDecision,
    ProviderReferenceSet,
)
from app.services.payment_provider_validation import (
    record_provider_validation,
    verify_webhook_signature,
)
from app.services.promotion_rollout import PromotionGateSnapshot
from app.services.promotion_rollout_status import read_promotion_rollout_status


def _db(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'provider-validation.db'}")
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)


def _references() -> ProviderReferenceSet:
    return ProviderReferenceSet(
        provider="stripe",
        mode=ProviderMode.SANDBOX,
        api_credential_reference="secret://stripe/test/api",
        webhook_secret_reference="secret://stripe/test/webhook",
        beta_price_reference="price_test_beta",
        founding_price_reference="price_test_founding",
        currency="USD",
        account_mode=ProviderMode.SANDBOX,
        validated_at=None,
        validation_digest=None,
    )


def _gates() -> PromotionGateSnapshot:
    return PromotionGateSnapshot(
        promotions_enabled=False,
        paid_beta_authorized=False,
        beta_lifetime_discount_enabled=False,
        founding_subscriber_enrollment_enabled=False,
        provider_ready=False,
    )


def test_provider_validation_is_persisted_and_audited(tmp_path: Path) -> None:
    engine, session_factory = _db(tmp_path)
    now = datetime(2026, 7, 28, 12, 0)
    decision = ProviderReadinessDecision(True, "provider_ready", "d" * 64)
    with session_factory() as db:
        record = record_provider_validation(
            db,
            references=_references(),
            decision=decision,
            actor_type="operator",
            actor_reference="admin@example.com",
            validated_at=now,
        )
        db.commit()
        assert record.validation_status == "valid"
        assert record.expires_at == now + timedelta(hours=24)
        assert db.scalar(select(PromotionAuditRecord).where(
            PromotionAuditRecord.event_type == "payment_provider_validation_recorded"
        )) is not None
    engine.dispose()


def test_rollout_status_reports_latest_provider_validation(tmp_path: Path) -> None:
    engine, session_factory = _db(tmp_path)
    now = datetime(2026, 7, 28, 12, 0)
    with session_factory() as db:
        record_provider_validation(
            db,
            references=_references(),
            decision=ProviderReadinessDecision(False, "provider_validation_stale", "a" * 64),
            actor_type="system",
            actor_reference="provider-readiness",
            validated_at=now,
        )
        db.commit()
    with session_factory() as db:
        status = read_promotion_rollout_status(db, gates=_gates())
        assert status.provider_validation_status == "invalid"
        assert status.provider_validation_reason == "provider_validation_stale"
        assert status.provider_validation_digest == "a" * 64
    engine.dispose()


def test_webhook_signature_is_bounded_and_constant_time_compatible() -> None:
    now = datetime(2026, 7, 28, 12, 0)
    payload = b'{"id":"evt_1"}'
    secret = b"test-secret-never-persisted"
    signed = str(int(now.timestamp())).encode("ascii") + b"." + payload
    signature = hmac.new(secret, signed, hashlib.sha256).hexdigest()
    assert verify_webhook_signature(
        payload=payload,
        signature_hex=signature,
        timestamp=now,
        now=now,
        secret=secret,
    ) is True
    assert verify_webhook_signature(
        payload=payload,
        signature_hex=signature,
        timestamp=now - timedelta(minutes=6),
        now=now,
        secret=secret,
    ) is False
    assert verify_webhook_signature(
        payload=payload + b"x",
        signature_hex=signature,
        timestamp=now,
        now=now,
        secret=secret,
    ) is False


def test_migration_and_model_are_registered() -> None:
    migration = Path(__file__).parents[1] / "alembic" / "versions" / "0039_payment_provider_validation.py"
    text = migration.read_text(encoding="utf-8")
    assert 'revision = "0039_provider_validation"' in text
    assert 'down_revision = "0038_promotion_rollout"' in text
    assert "payment_provider_validations" in Base.metadata.tables
