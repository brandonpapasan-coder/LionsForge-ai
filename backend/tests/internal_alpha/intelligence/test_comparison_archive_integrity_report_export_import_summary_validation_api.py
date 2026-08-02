import pytest
from pydantic import ValidationError

from app.api.deps import get_current_user
from app.api.routes import (
    internal_alpha_comparison_archive_integrity_report_export_bundles as routes,
)
from app.main import app


def test_summary_validation_route_forwards_exact_summary_and_findings(monkeypatch) -> None:
    summary = {"summary": True}
    captured: dict[str, object] = {}

    def fake_validator(candidate_summary):
        captured["summary"] = candidate_summary
        return ["canonical payload digest mismatch"]

    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_integrity_report_export_import_summary",
        fake_validator,
    )
    payload = routes.IntelligenceComparisonArchiveIntegrityReportExportImportSummaryValidationInput(
        summary=summary,
    )
    result = routes.validate_internal_alpha_intelligence_comparison_archive_integrity_report_export_import_summary(
        payload,
        current_user=object(),  # type: ignore[arg-type]
    )
    assert captured["summary"] == summary
    assert result["valid"] is False
    assert result["findings"] == ["canonical payload digest mismatch"]
    assert "does not infer causality" in result["interpretation_notice"]


def test_summary_validation_model_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        routes.IntelligenceComparisonArchiveIntegrityReportExportImportSummaryValidationInput.model_validate(
            {"summary": {}, "extra": True}
        )


def test_summary_validation_route_requires_authentication() -> None:
    target = next(
        route
        for route in routes.router.routes
        if route.path.endswith("/import-summary/validate")
    )
    dependency_calls = [dependency.call for dependency in target.dependant.dependencies]
    assert get_current_user in dependency_calls


def test_application_registers_exact_import_summary_validation_path() -> None:
    path = (
        "/api/v1/internal-alpha/intelligence/comparison/archive/integrity-report/"
        "export-bundle/import-summary/validate"
    )
    assert path in app.openapi()["paths"]
