import pytest
from pydantic import ValidationError

from app.api.routes.internal_alpha_comparison_archive_integrity_report_export_import_summary_batch_pipeline import (
    IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineResponse,
    IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineVerificationResponse,
)
from app.main import app


_BASE_PATH = (
    "/api/v1/internal-alpha/intelligence/comparison/archive/integrity-report/"
    "export-bundle/import-summary/batch-pipeline"
)
_PIPELINE_SCHEMA = (
    "#/components/schemas/"
    "IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineResponse"
)
_VERIFICATION_SCHEMA = (
    "#/components/schemas/"
    "IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineVerificationResponse"
)


def test_pipeline_routes_publish_explicit_response_schemas() -> None:
    paths = app.openapi()["paths"]

    assert paths[_BASE_PATH]["post"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"] == _PIPELINE_SCHEMA
    for suffix in ("/validate", "/validate-response"):
        assert paths[_BASE_PATH + suffix]["post"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]["$ref"] == _VERIFICATION_SCHEMA


def test_pipeline_response_model_accepts_only_canonical_shape() -> None:
    response = IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineResponse(
        batch_result={},
        diagnostics={},
        occurrence_projection={},
        interpretation_notice="bounded",
    )

    assert response.model_dump() == {
        "batch_result": {},
        "diagnostics": {},
        "occurrence_projection": {},
        "interpretation_notice": "bounded",
    }

    with pytest.raises(ValidationError):
        IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineResponse.model_validate(
            {
                "batch_result": {},
                "diagnostics": {},
                "occurrence_projection": {},
                "interpretation_notice": "bounded",
                "unexpected": True,
            }
        )


@pytest.mark.parametrize(
    "payload",
    (
        {"valid": 1, "findings": [], "interpretation_notice": "bounded"},
        {"valid": True, "findings": [1], "interpretation_notice": "bounded"},
        {"valid": True, "findings": [], "interpretation_notice": 1},
        {
            "valid": True,
            "findings": [],
            "interpretation_notice": "bounded",
            "unexpected": True,
        },
    ),
)
def test_verification_response_model_rejects_noncanonical_values(payload: dict) -> None:
    with pytest.raises(ValidationError):
        IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineVerificationResponse.model_validate(
            payload
        )
