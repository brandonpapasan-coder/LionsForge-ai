import pytest
from pydantic import ValidationError

from app.api.deps import get_current_user
from app.api.routes import (
    internal_alpha_comparison_archive_integrity_report_export_bundles as routes,
)
from app.internal_alpha.intelligence import (
    comparison_archive_integrity_report_export_import_summary_batch as batches,
)
from app.main import app


def test_batch_preserves_order_and_aggregates_findings(monkeypatch) -> None:
    summaries = [{"id": "a"}, {"id": "b"}, {"id": "c"}]

    def fake_validator(summary):
        return [] if summary["id"] != "b" else ["payload digest mismatch", "notice mismatch"]

    monkeypatch.setattr(
        batches,
        "validate_intelligence_comparison_archive_integrity_report_export_import_summary",
        fake_validator,
    )
    result = batches.validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch(
        summaries
    )
    assert result["summary_count"] == 3
    assert result["valid_count"] == 2
    assert result["invalid_count"] == 1
    assert result["finding_count"] == 2
    assert result["results"] == [
        {"index": 0, "valid": True, "findings": []},
        {
            "index": 1,
            "valid": False,
            "findings": ["payload digest mismatch", "notice mismatch"],
        },
        {"index": 2, "valid": True, "findings": []},
    ]
    assert "does not authorize" in result["interpretation_notice"]


def test_batch_rejects_empty_oversized_and_non_list_inputs() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        batches.validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch([])
    with pytest.raises(ValueError, match="exceeds item limit"):
        batches.validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch(
            [{}] * 101
        )
    with pytest.raises(TypeError, match="must be a list"):
        batches.validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch(  # type: ignore[arg-type]
            {}
        )


def test_batch_marks_non_object_entries_invalid(monkeypatch) -> None:
    monkeypatch.setattr(
        batches,
        "validate_intelligence_comparison_archive_integrity_report_export_import_summary",
        lambda summary: [],
    )
    result = batches.validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch(  # type: ignore[list-item]
        [{}, []]
    )
    assert result["valid_count"] == 1
    assert result["invalid_count"] == 1
    assert result["results"][1]["findings"] == [
        "integrity report export import summary must be an object"
    ]


def test_batch_route_forwards_exact_ordered_summaries(monkeypatch) -> None:
    summaries = [{"id": "a"}, {"id": "b"}]
    expected = {"summary_count": 2}
    captured: dict[str, object] = {}

    def fake_batch_validator(candidate_summaries):
        captured["summaries"] = candidate_summaries
        return expected

    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch",
        fake_batch_validator,
    )
    payload = routes.IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchValidationInput(
        summaries=summaries
    )
    result = routes.validate_internal_alpha_intelligence_comparison_archive_integrity_report_export_import_summary_batch(
        payload,
        current_user=object(),  # type: ignore[arg-type]
    )
    assert result is expected
    assert captured["summaries"] == summaries


def test_batch_request_model_enforces_bounds_and_unknown_field_rejection() -> None:
    with pytest.raises(ValidationError):
        routes.IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchValidationInput(
            summaries=[]
        )
    with pytest.raises(ValidationError):
        routes.IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchValidationInput(
            summaries=[{}] * 101
        )
    with pytest.raises(ValidationError):
        routes.IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchValidationInput.model_validate(
            {"summaries": [{}], "extra": True}
        )


def test_batch_route_requires_authentication_and_is_registered() -> None:
    target = next(
        route
        for route in routes.router.routes
        if route.path.endswith("/import-summary/validate-batch")
    )
    dependency_calls = [dependency.call for dependency in target.dependant.dependencies]
    assert get_current_user in dependency_calls

    path = (
        "/api/v1/internal-alpha/intelligence/comparison/archive/integrity-report/"
        "export-bundle/import-summary/validate-batch"
    )
    assert path in app.openapi()["paths"]
