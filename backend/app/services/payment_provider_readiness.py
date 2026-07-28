from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Mapping, Protocol


class ProviderMode(StrEnum):
    SANDBOX = "sandbox"
    LIVE = "live"


@dataclass(frozen=True)
class ProviderReferenceSet:
    provider: str
    mode: ProviderMode
    api_credential_reference: str | None
    webhook_secret_reference: str | None
    beta_price_reference: str | None
    founding_price_reference: str | None
    currency: str
    account_mode: ProviderMode
    validated_at: datetime | None
    validation_digest: str | None


@dataclass(frozen=True)
class ProviderReadinessDecision:
    ready: bool
    reason_code: str
    configuration_digest: str


@dataclass(frozen=True)
class InternalCheckoutRequest:
    account_id: int
    eligibility_id: int
    promotion_type: str
    idempotency_key: str
    amount_minor: int
    currency: str
    success_url: str
    cancel_url: str
    metadata: Mapping[str, str]


@dataclass(frozen=True)
class NormalizedCheckoutSession:
    provider_session_id: str
    checkout_url: str
    status: str
    provider: str


class SecretResolver(Protocol):
    def exists(self, reference: str) -> bool: ...


class CheckoutProviderAdapter(Protocol):
    def create_checkout_session(
        self,
        *,
        credential_reference: str,
        request: InternalCheckoutRequest,
    ) -> Mapping[str, object]: ...


SUPPORTED_CURRENCIES = {"USD"}
VALIDATION_MAX_AGE = timedelta(hours=24)


def provider_configuration_digest(references: ProviderReferenceSet) -> str:
    payload = {
        "provider": references.provider,
        "mode": references.mode.value,
        "api_credential_reference": references.api_credential_reference,
        "webhook_secret_reference": references.webhook_secret_reference,
        "beta_price_reference": references.beta_price_reference,
        "founding_price_reference": references.founding_price_reference,
        "currency": references.currency.upper(),
        "account_mode": references.account_mode.value,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def evaluate_provider_readiness(
    references: ProviderReferenceSet,
    *,
    now: datetime,
    secret_resolver: SecretResolver,
) -> ProviderReadinessDecision:
    digest = provider_configuration_digest(references)

    def deny(reason_code: str) -> ProviderReadinessDecision:
        return ProviderReadinessDecision(False, reason_code, digest)

    if references.mode != references.account_mode:
        return deny("provider_mode_mismatch")
    if references.mode == ProviderMode.LIVE:
        return deny("live_provider_mode_not_authorized")
    if references.currency.upper() not in SUPPORTED_CURRENCIES:
        return deny("unsupported_provider_currency")
    if not references.api_credential_reference:
        return deny("provider_api_reference_missing")
    if not references.webhook_secret_reference:
        return deny("provider_webhook_reference_missing")
    if not references.beta_price_reference or not references.founding_price_reference:
        return deny("provider_price_reference_missing")
    if not secret_resolver.exists(references.api_credential_reference):
        return deny("provider_api_secret_unresolved")
    if not secret_resolver.exists(references.webhook_secret_reference):
        return deny("provider_webhook_secret_unresolved")
    if references.validated_at is None or references.validation_digest is None:
        return deny("provider_configuration_unvalidated")
    if now - references.validated_at > VALIDATION_MAX_AGE:
        return deny("provider_validation_stale")
    if references.validation_digest != digest:
        return deny("provider_validation_digest_mismatch")
    return ProviderReadinessDecision(True, "provider_ready", digest)


def create_internal_checkout_session(
    *,
    references: ProviderReferenceSet,
    readiness: ProviderReadinessDecision,
    request: InternalCheckoutRequest,
    adapter: CheckoutProviderAdapter,
) -> NormalizedCheckoutSession:
    if not readiness.ready:
        raise RuntimeError(f"provider not ready: {readiness.reason_code}")
    if references.mode != ProviderMode.SANDBOX:
        raise RuntimeError("internal checkout requires sandbox provider mode")
    if request.currency.upper() != references.currency.upper():
        raise RuntimeError("checkout currency does not match provider configuration")
    if not references.api_credential_reference:
        raise RuntimeError("provider credential reference is unavailable")

    raw = adapter.create_checkout_session(
        credential_reference=references.api_credential_reference,
        request=request,
    )
    session_id = raw.get("id")
    checkout_url = raw.get("url")
    status = raw.get("status", "created")
    if not isinstance(session_id, str) or not session_id:
        raise RuntimeError("provider response omitted session id")
    if not isinstance(checkout_url, str) or not checkout_url.startswith("https://"):
        raise RuntimeError("provider response omitted secure checkout URL")
    if not isinstance(status, str):
        raise RuntimeError("provider response status is invalid")

    return NormalizedCheckoutSession(
        provider_session_id=session_id,
        checkout_url=checkout_url,
        status=status,
        provider=references.provider,
    )
