import copy

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
_PIPELINE_SCHEMA_NAME = (
    "IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineResponse"
)
_PIPELINE_OUTPUT_SCHEMA = f"#/components/schemas/{_PIPELINE_SCHEMA_NAME}-Output"
_VERIFICATION_SCHEMA = (
    "#/components/schemas/"
    "IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineVerificationResponse"
)


def canonical_pipeline_response() -> dict:
    return {
        "batch_result": {
            "summary_count": 1,
            "valid_count": 0,
            "invalid_count": 1,
            "finding_count": 1,
            "results": [
                {
                    "index": 0,
                    "valid": False,
                    "findings": ["bounded finding"],
                }
            ],
            "interpretation_notice": "bounded batch result",
        },
        "diagnostics": {
            "summary_count": 1,
            "invalid_summary_count": 1,
            "invalid_indexes": [0],
            "distinct_finding_count": 1,
            "finding_count": 1,
            "finding_frequencies": [
                {
                    "finding": "bounded finding",
                    "count": 1,
                }
            ],
            "interpretation_notice": "bounded diagnostics",
        },
        "occurrence_projection": {
            "summary_count": 1,
            "finding_count": 1,
            "distinct_finding_count": 1,
            "occurrences": [
                {
                    "finding": "bounded finding",
                    "occurrence_count": 1,
                    "affected_summary_count": 1,
                    "summary_indexes": [0],
                }
            ],
            "interpretation_notice": "bounded occurrences",
        },
        "interpretation_notice": "bounded pipeline",
    }


def test_pipeline_routes_publish_explicit_response_schemas() -> None:
    paths = app.openapi()["paths"]

    assert paths[_BASE_PATH]["post"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"] == _PIPELINE_OUTPUT_SCHEMA
    for suffix in ("/validate", "/validate-response"):
        assert paths[_BASE_PATH + suffix]["post"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]["$ref"] == _VERIFICATION_SCHEMA


def test_pipeline_openapi_publishes_nested_artifact_models() -> None:
    schemas = app.openapi()["components"]["schemas"]
    pipeline = schemas[f"{_PIPELINE_SCHEMA_NAME}-Output"]

    assert pipeline["properties"]["batch_result"]["$ref"].endswith(
        "IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchResult-Output"
    )
    assert pipeline["properties"]["diagnostics"]["$ref"].endswith(
        "IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchDiagnostics-Output"
    )
    assert pipeline["properties"]["occurrence_projection"]["$ref"].endswith(
        "IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchOccurrenceProjection-Output"
    )


def test_pipeline_response_model_accepts_canonical_nested_shape() -> None:
    payload = canonical_pipeline_response()

    response = IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineResponse.model_validate(
        payload
    )

    assert response.model_dump() == payload


@pytest.mark.parametrize(
    ("path", "value"),
    (
        (("batch_result", "results", 0, "valid"), 0),
        (("batch_result", "results", 0, "findings"), [1]),
        (("diagnostics", "invalid_indexes"), ["0"]),
        (("diagnostics", "finding_frequencies", 0, "count"), "1"),
        (("occurrence_projection", "occurrences", 0, "summary_indexes"), [False]),
        (("occurrence_projection", "finding_count"), -1),
    ),
)
def test_pipeline_response_model_rejects_noncanonical_nested_values(
    path: tuple,
    value: object,
) -> None:
    payload = copy.deepcopy(canonical_pipeline_response())
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value

    with pytest.raises(ValidationError):
        IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineResponse.model_validate(
            payload
        )


@pytest.mark.parametrize(
    "path",
    (
        ("batch_result",),
        ("batch_result", "results", 0),
        ("diagnostics",),
        ("diagnostics", "finding_frequencies", 0),
        ("occurrence_projection",),
        ("occurrence_projection", "occurrences", 0),
    ),
)
def test_pipeline_response_model_rejects_nested_extra_fields(path: tuple) -> None:
    payload = copy.deepcopy(canonical_pipeline_response())
    target = payload
    for key in path:
        target = target[key]
    target["unexpected"] = True

    with pytest.raises(ValidationError):
        IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineResponse.model_validate(
            payload
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
