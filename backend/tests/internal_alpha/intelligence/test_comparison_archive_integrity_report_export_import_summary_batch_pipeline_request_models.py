from app.main import app


_BASE_PATH = (
    "/api/v1/internal-alpha/intelligence/comparison/archive/integrity-report/"
    "export-bundle/import-summary/batch-pipeline"
)
_SCHEMA_PREFIX = "#/components/schemas/"
_PIPELINE_RESPONSE = (
    "IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineResponse"
)
_PIPELINE_VERIFICATION_RESPONSE = (
    "IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineVerificationResponse"
)


def _request_schema(path: str) -> dict:
    return app.openapi()["paths"][path]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]


def test_pipeline_routes_publish_explicit_request_models() -> None:
    assert _request_schema(_BASE_PATH)["$ref"] == (
        _SCHEMA_PREFIX
        + "IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineInput"
    )
    assert _request_schema(_BASE_PATH + "/validate")["$ref"] == (
        _SCHEMA_PREFIX
        + "IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineValidationInput"
    )
    assert _request_schema(_BASE_PATH + "/validate-response")["$ref"] == (
        _SCHEMA_PREFIX
        + "IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineValidationResponseInput"
    )


def test_pipeline_validation_requests_reference_strict_input_artifacts() -> None:
    schemas = app.openapi()["components"]["schemas"]
    validation = schemas[
        "IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineValidationInput"
    ]
    validation_response = schemas[
        "IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineValidationResponseInput"
    ]

    assert validation["additionalProperties"] is False
    assert validation["properties"]["pipeline"]["$ref"] == (
        _SCHEMA_PREFIX + _PIPELINE_RESPONSE + "-Input"
    )
    assert validation_response["additionalProperties"] is False
    assert validation_response["properties"]["pipeline"]["$ref"] == (
        _SCHEMA_PREFIX + _PIPELINE_RESPONSE + "-Input"
    )
    assert validation_response["properties"]["response"]["$ref"] == (
        _SCHEMA_PREFIX + _PIPELINE_VERIFICATION_RESPONSE
    )


def test_pipeline_input_schema_bounds_summary_count() -> None:
    schemas = app.openapi()["components"]["schemas"]
    pipeline_input = schemas[
        "IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineInput"
    ]
    summaries = pipeline_input["properties"]["summaries"]

    assert pipeline_input["additionalProperties"] is False
    assert summaries["minItems"] == 1
    assert summaries["maxItems"] == 100
