import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from app.api.deps import get_current_user
from app.api.routes import (
    internal_alpha_comparison_archive_integrity_report_export_bundles as routes,
)
from app.api.routes.internal_alpha_comparison_archive_integrity_reports import (
    router as parent_router,
)


def test_create_route_forwards_exact_payload(monkeypatch) -> None:
    report = {"report": True}
    receipt = {"receipt": True}
    manifest = {"manifest": True}
    expected = {"bundle": True}
    captured: dict[str, object] = {}

    def fake_builder(candidate_report, candidate_receipt, candidate_manifest):
        captured["report"] = candidate_report
        captured["receipt"] = candidate_receipt
        captured["manifest"] = candidate_manifest
        return expected

    monkeypatch.setattr(
        routes,
        "build_intelligence_comparison_archive_integrity_report_export_bundle",
        fake_builder,
    )
    payload = routes.IntelligenceComparisonArchiveIntegrityReportExportBundleInput(
        report=report,
        receipt=receipt,
        manifest=manifest,
    )

    result = routes.create_internal_alpha_intelligence_comparison_archive_integrity_report_export_bundle(
        payload,
        current_user=object(),  # type: ignore[arg-type]
    )

    assert result is expected
    assert captured == {
        "report": report,
        "receipt": receipt,
        "manifest": manifest,
    }


def test_validation_route_forwards_bundle_and_returns_fail_closed_findings(monkeypatch) -> None:
    bundle = {"bundle": True}
    captured: dict[str, object] = {}

    def fake_validator(candidate_bundle):
        captured["bundle"] = candidate_bundle
        return ["bundle digest mismatch"]

    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_integrity_report_export_bundle",
        fake_validator,
    )
    payload = routes.IntelligenceComparisonArchiveIntegrityReportExportBundleValidationInput(
        bundle=bundle,
    )

    result = routes.validate_internal_alpha_intelligence_comparison_archive_integrity_report_export_bundle(
        payload,
        current_user=object(),  # type: ignore[arg-type]
    )

    assert captured["bundle"] is bundle
    assert result["valid"] is False
    assert result["findings"] == ["bundle digest mismatch"]
    assert "does not infer causality" in result["interpretation_notice"]


def test_request_models_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        routes.IntelligenceComparisonArchiveIntegrityReportExportBundleInput.model_validate(
            {
                "report": {},
                "receipt": {},
                "manifest": {},
                "extra": True,
            }
        )

    with pytest.raises(ValidationError):
        routes.IntelligenceComparisonArchiveIntegrityReportExportBundleValidationInput.model_validate(
            {"bundle": {}, "extra": True}
        )


def test_routes_require_authentication_dependency() -> None:
    for route in routes.router.routes:
        dependency_calls = [dependency.call for dependency in route.dependant.dependencies]
        assert get_current_user in dependency_calls


def test_parent_router_registers_exact_export_bundle_paths() -> None:
    app = FastAPI()
    app.include_router(
        parent_router,
        prefix="/api/internal-alpha/intelligence",
    )
    paths = app.openapi()["paths"]

    assert "/api/internal-alpha/intelligence/comparison/archive/integrity-report/export-bundle" in paths
    assert "/api/internal-alpha/intelligence/comparison/archive/integrity-report/export-bundle/validate" in paths
