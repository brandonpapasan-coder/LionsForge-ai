import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.deps import get_current_user
from app.api.routes import (
    internal_alpha_comparison_archive_integrity_report_export_bundles as routes,
)
from app.main import app


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
    assert captured == {"report": report, "receipt": receipt, "manifest": manifest}


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
    assert captured["bundle"] == bundle
    assert result["valid"] is False
    assert result["findings"] == ["bundle digest mismatch"]
    assert "does not infer causality" in result["interpretation_notice"]


def test_download_route_returns_canonical_attachment(monkeypatch) -> None:
    bundle = {"bundle": True}
    captured: dict[str, object] = {}

    def fake_serializer(candidate_bundle):
        captured["bundle"] = candidate_bundle
        return b'{"bundle":true}'

    monkeypatch.setattr(
        routes,
        "serialize_intelligence_comparison_archive_integrity_report_export_bundle",
        fake_serializer,
    )
    payload = routes.IntelligenceComparisonArchiveIntegrityReportExportBundleValidationInput(
        bundle=bundle,
    )
    response = routes.download_internal_alpha_intelligence_comparison_archive_integrity_report_export_bundle(
        payload,
        current_user=object(),  # type: ignore[arg-type]
    )
    assert captured["bundle"] == bundle
    assert response.body == b'{"bundle":true}'
    assert response.media_type == "application/json"
    assert response.headers["content-disposition"] == (
        'attachment; filename="comparison-archive-integrity-report-export-bundle.json"'
    )
    assert response.headers["x-content-type-options"] == "nosniff"


def test_import_route_forwards_exact_utf8_bytes_and_returns_summary(monkeypatch) -> None:
    expected = {
        "bundle": {"bundle": True},
        "canonical_byte_count": 15,
        "canonical_payload_sha256": "a" * 64,
        "export_bundle_sha256": "b" * 64,
        "interpretation_notice": "notice",
    }
    captured: dict[str, object] = {}

    def fake_summarizer(candidate_content):
        captured["content"] = candidate_content
        return expected

    monkeypatch.setattr(
        routes,
        "summarize_intelligence_comparison_archive_integrity_report_export_import",
        fake_summarizer,
    )
    payload = routes.IntelligenceComparisonArchiveIntegrityReportExportBundleImportInput(
        content='{"bundle":true}',
    )
    result = routes.import_internal_alpha_intelligence_comparison_archive_integrity_report_export_bundle(
        payload,
        current_user=object(),  # type: ignore[arg-type]
    )
    assert result is expected
    assert captured["content"] == b'{"bundle":true}'


def test_import_route_maps_invalid_content_to_controlled_422(monkeypatch) -> None:
    monkeypatch.setattr(
        routes,
        "summarize_intelligence_comparison_archive_integrity_report_export_import",
        lambda candidate_content: (_ for _ in ()).throw(ValueError("bundle digest mismatch")),
    )
    payload = routes.IntelligenceComparisonArchiveIntegrityReportExportBundleImportInput(
        content='{"bundle":false}',
    )
    with pytest.raises(HTTPException) as exc_info:
        routes.import_internal_alpha_intelligence_comparison_archive_integrity_report_export_bundle(
            payload,
            current_user=object(),  # type: ignore[arg-type]
        )
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "bundle digest mismatch"


def test_request_models_reject_unknown_fields_and_invalid_import_sizes() -> None:
    with pytest.raises(ValidationError):
        routes.IntelligenceComparisonArchiveIntegrityReportExportBundleInput.model_validate(
            {"report": {}, "receipt": {}, "manifest": {}, "extra": True}
        )
    with pytest.raises(ValidationError):
        routes.IntelligenceComparisonArchiveIntegrityReportExportBundleValidationInput.model_validate(
            {"bundle": {}, "extra": True}
        )
    with pytest.raises(ValidationError):
        routes.IntelligenceComparisonArchiveIntegrityReportExportBundleImportInput.model_validate(
            {"content": "", "extra": True}
        )
    with pytest.raises(ValidationError):
        routes.IntelligenceComparisonArchiveIntegrityReportExportBundleImportInput(
            content="x" * 1_000_001,
        )


def test_routes_require_authentication_dependency() -> None:
    for route in routes.router.routes:
        dependency_calls = [dependency.call for dependency in route.dependant.dependencies]
        assert get_current_user in dependency_calls


def test_application_registers_exact_export_bundle_paths() -> None:
    paths = app.openapi()["paths"]
    base = "/api/v1/internal-alpha/intelligence/comparison/archive/integrity-report/export-bundle"
    assert base in paths
    assert f"{base}/validate" in paths
    assert f"{base}/download" in paths
    assert f"{base}/import" in paths
