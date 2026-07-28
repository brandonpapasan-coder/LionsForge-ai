from datetime import datetime, timedelta

import pytest

from app.services.payment_provider_readiness import (
    InternalCheckoutRequest,
    ProviderMode,
    ProviderReferenceSet,
    create_internal_checkout_session,
    evaluate_provider_readiness,
    provider_configuration_digest,
)


class Resolver:
    def __init__(self, available: set[str]) -> None:
        self.available = available

    def exists(self, reference: str) -> bool:
        return reference in self.available


class Adapter:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response
        self.credential_reference: str | None = None

    def create_checkout_session(self, *, credential_reference: str, request: InternalCheckoutRequest):
        self.credential_reference = credential_reference
        assert request.account_id == 7
        return self.response


def references(now: datetime) -> ProviderReferenceSet:
    draft = ProviderReferenceSet(
        provider="stripe",
        mode=ProviderMode.SANDBOX,
        api_credential_reference="secret://payments/stripe/test/api",
        webhook_secret_reference="secret://payments/stripe/test/webhook",
        beta_price_reference="price_test_beta",
        founding_price_reference="price_test_founding",
        currency="USD",
        account_mode=ProviderMode.SANDBOX,
        validated_at=now,
        validation_digest=None,
    )
    return ProviderReferenceSet(**{**draft.__dict__, "validation_digest": provider_configuration_digest(draft)})


def resolver() -> Resolver:
    return Resolver({"secret://payments/stripe/test/api", "secret://payments/stripe/test/webhook"})


def test_complete_sandbox_configuration_is_ready() -> None:
    now = datetime(2026, 7, 28, 12, 0, 0)
    decision = evaluate_provider_readiness(references(now), now=now, secret_resolver=resolver())
    assert decision.ready is True
    assert decision.reason_code == "provider_ready"


def test_live_mode_is_fail_closed() -> None:
    now = datetime(2026, 7, 28, 12, 0, 0)
    current = references(now)
    live = ProviderReferenceSet(**{**current.__dict__, "mode": ProviderMode.LIVE, "account_mode": ProviderMode.LIVE})
    decision = evaluate_provider_readiness(live, now=now, secret_resolver=resolver())
    assert decision.reason_code == "live_provider_mode_not_authorized"


def test_mixed_provider_modes_are_rejected() -> None:
    now = datetime(2026, 7, 28, 12, 0, 0)
    current = references(now)
    mixed = ProviderReferenceSet(**{**current.__dict__, "account_mode": ProviderMode.LIVE})
    decision = evaluate_provider_readiness(mixed, now=now, secret_resolver=resolver())
    assert decision.reason_code == "provider_mode_mismatch"


def test_stale_validation_is_not_ready() -> None:
    validated_at = datetime(2026, 7, 27, 10, 0, 0)
    decision = evaluate_provider_readiness(
        references(validated_at),
        now=validated_at + timedelta(hours=25),
        secret_resolver=resolver(),
    )
    assert decision.reason_code == "provider_validation_stale"


def test_missing_secret_reference_is_not_ready() -> None:
    now = datetime(2026, 7, 28, 12, 0, 0)
    decision = evaluate_provider_readiness(references(now), now=now, secret_resolver=Resolver(set()))
    assert decision.reason_code == "provider_api_secret_unresolved"


def test_unsupported_currency_is_not_ready() -> None:
    now = datetime(2026, 7, 28, 12, 0, 0)
    current = references(now)
    changed = ProviderReferenceSet(**{**current.__dict__, "currency": "EUR"})
    decision = evaluate_provider_readiness(changed, now=now, secret_resolver=resolver())
    assert decision.reason_code == "unsupported_provider_currency"


def test_digest_change_invalidates_validation() -> None:
    now = datetime(2026, 7, 28, 12, 0, 0)
    current = references(now)
    changed = ProviderReferenceSet(**{**current.__dict__, "founding_price_reference": "price_test_changed"})
    decision = evaluate_provider_readiness(changed, now=now, secret_resolver=resolver())
    assert decision.reason_code == "provider_validation_digest_mismatch"


def test_internal_checkout_normalizes_only_safe_fields() -> None:
    now = datetime(2026, 7, 28, 12, 0, 0)
    current = references(now)
    readiness = evaluate_provider_readiness(current, now=now, secret_resolver=resolver())
    adapter = Adapter(
        {
            "id": "cs_test_123",
            "url": "https://checkout.example.test/session/cs_test_123",
            "status": "open",
            "client_secret": "must-not-be-returned",
        }
    )
    result = create_internal_checkout_session(
        references=current,
        readiness=readiness,
        request=InternalCheckoutRequest(
            account_id=7,
            eligibility_id=11,
            promotion_type="beta",
            idempotency_key="eligibility-11-attempt-1",
            amount_minor=500,
            currency="USD",
            success_url="https://internal.example.test/success",
            cancel_url="https://internal.example.test/cancel",
            metadata={"eligibility_id": "11"},
        ),
        adapter=adapter,
    )
    assert result.provider_session_id == "cs_test_123"
    assert result.checkout_url.startswith("https://")
    assert not hasattr(result, "client_secret")
    assert adapter.credential_reference == "secret://payments/stripe/test/api"


def test_internal_checkout_rejects_unready_provider() -> None:
    now = datetime(2026, 7, 28, 12, 0, 0)
    current = references(now)
    readiness = evaluate_provider_readiness(current, now=now, secret_resolver=Resolver(set()))
    with pytest.raises(RuntimeError, match="provider not ready"):
        create_internal_checkout_session(
            references=current,
            readiness=readiness,
            request=InternalCheckoutRequest(
                account_id=7,
                eligibility_id=11,
                promotion_type="beta",
                idempotency_key="key",
                amount_minor=500,
                currency="USD",
                success_url="https://internal.example.test/success",
                cancel_url="https://internal.example.test/cancel",
                metadata={},
            ),
            adapter=Adapter({}),
        )
