from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException

from app.api.router import api_router
from app.api.routes.sandbox_payment_verification import _require_operator
from app.models.sandbox_payment_verification import (
    SandboxPaymentVerificationEvidence,
    SandboxPaymentVerificationRun,
)


class _User:
    def __init__(self, *, is_superuser: bool) -> None:
        self.is_superuser = is_superuser


def test_operator_guard_allows_superusers_and_rejects_other_users() -> None:
    _require_operator(_User(is_superuser=True))
    with pytest.raises(HTTPException) as exc_info:
        _require_operator(_User(is_superuser=False))
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Operator access required"


def test_sandbox_verification_routes_are_registered() -> None:
    app = FastAPI()
    app.include_router(api_router)
    paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert "/sandbox-payment-verification/runs" in paths
    assert "/sandbox-payment-verification/runs/{run_id}" in paths


def test_model_registry_exports_verification_models() -> None:
    import app.models as models

    assert models.SandboxPaymentVerificationRun is SandboxPaymentVerificationRun
    assert models.SandboxPaymentVerificationEvidence is SandboxPaymentVerificationEvidence


def test_route_implementation_is_bounded_and_fails_closed_without_adapters() -> None:
    source = Path("app/api/routes/sandbox_payment_verification.py").read_text(encoding="utf-8")
    assert ".limit(100)" in source
    assert 'getattr(request.app.state, "sandbox_checkout_executor", None)' in source
    assert 'getattr(request.app.state, "sandbox_webhook_verifier", None)' in source
    assert "HTTP_503_SERVICE_UNAVAILABLE" in source
    assert "db.rollback()" in source


def test_router_registration_is_unconditional_and_operator_only_surface() -> None:
    router_source = Path("app/api/router.py").read_text(encoding="utf-8")
    route_source = Path("app/api/routes/sandbox_payment_verification.py").read_text(encoding="utf-8")
    assert "sandbox_payment_verification.router" in router_source
    assert 'prefix="/sandbox-payment-verification"' in router_source
    assert route_source.count("_require_operator(current_user)") == 3


def test_migration_and_models_are_registered_structurally() -> None:
    migration = Path("alembic/versions/0040_sandbox_payment_verification.py").read_text(encoding="utf-8")
    models_init = Path("app/models/__init__.py").read_text(encoding="utf-8")
    assert 'revision = "0040_sandbox_payment_verify"' in migration
    assert 'down_revision = "0039_provider_validation"' in migration
    assert "sandbox_payment_verification_runs" in migration
    assert "sandbox_payment_verification_evidence" in migration
    assert "SandboxPaymentVerificationRun" in models_init
    assert "SandboxPaymentVerificationEvidence" in models_init
