import pytest
from pydantic import ValidationError

from app.api.routes.internal_alpha_comparison_archive_integrity_report_export_bundles import (
    IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchDiagnosticOccurrencesValidationInput,
    IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchDiagnosticOccurrencesValidationResponseInput,
    IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchDiagnosticsValidationInput,
    IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchResultValidationInput,
)


def _batch_result() -> dict[str, object]:
    return {
        "summary_count": 1,
        "valid_count": 1,
        "invalid_count": 0,
        "finding_count": 0,
        "results": [{"index": 0, "valid": True, "findings": []}],
        "interpretation_notice": "batch notice",
    }


def _diagnostics() -> dict[str, object]:
    return {
        "summary_count": 1,
        "invalid_summary_count": 0,
        "invalid_indexes": [],
        "distinct_finding_count": 0,
        "finding_count": 0,
        "finding_frequencies": [],
        "interpretation_notice": "diagnostics notice",
    }


def _occurrence_projection() -> dict[str, object]:
    return {
        "summary_count": 1,
        "finding_count": 0,
        "distinct_finding_count": 0,
        "occurrences": [],
        "interpretation_notice": "occurrence notice",
    }


def _validation_response() -> dict[str, object]:
    return {
        "valid": True,
        "findings": [],
        "interpretation_notice": "validation notice",
    }


def test_strict_artifact_inputs_accept_canonical_nested_envelopes() -> None:
    payload = (
        IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchDiagnosticOccurrencesValidationResponseInput.model_validate(
            {
                "summaries": [{}],
                "batch_result": _batch_result(),
                "diagnostics": _diagnostics(),
                "occurrence_projection": _occurrence_projection(),
                "validation_response": _validation_response(),
            }
        )
    )

    assert payload.batch_result.summary_count == 1
    assert payload.diagnostics.summary_count == 1
    assert payload.occurrence_projection.summary_count == 1
    assert payload.validation_response.valid is True


@pytest.mark.parametrize(
    ("model", "payload", "field"),
    [
        (
            IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchResultValidationInput,
            {"summaries": [{}], "batch_result": {**_batch_result(), "unexpected": True}},
            "batch_result",
        ),
        (
            IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchDiagnosticsValidationInput,
            {
                "summaries": [{}],
                "batch_result": _batch_result(),
                "diagnostics": {**_diagnostics(), "unexpected": True},
            },
            "diagnostics",
        ),
        (
            IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchDiagnosticOccurrencesValidationInput,
            {
                "summaries": [{}],
                "batch_result": _batch_result(),
                "diagnostics": _diagnostics(),
                "occurrence_projection": {
                    **_occurrence_projection(),
                    "unexpected": True,
                },
            },
            "occurrence_projection",
        ),
        (
            IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchDiagnosticOccurrencesValidationResponseInput,
            {
                "summaries": [{}],
                "batch_result": _batch_result(),
                "diagnostics": _diagnostics(),
                "occurrence_projection": _occurrence_projection(),
                "validation_response": {
                    **_validation_response(),
                    "unexpected": True,
                },
            },
            "validation_response",
        ),
    ],
)
def test_strict_artifact_inputs_reject_nested_extra_fields(
    model: type, payload: dict[str, object], field: str
) -> None:
    with pytest.raises(ValidationError) as exc_info:
        model.model_validate(payload)

    assert field in str(exc_info.value)
    assert "extra_forbidden" in str(exc_info.value)


def test_strict_artifact_inputs_reject_coercive_nested_types() -> None:
    payload = {
        "summaries": [{}],
        "batch_result": {**_batch_result(), "summary_count": "1"},
    }

    with pytest.raises(ValidationError) as exc_info:
        IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchResultValidationInput.model_validate(
            payload
        )

    assert "batch_result.summary_count" in str(exc_info.value)
    assert "int_type" in str(exc_info.value)


def test_strict_artifact_input_schemas_publish_concrete_nested_refs() -> None:
    schema = IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchDiagnosticOccurrencesValidationResponseInput.model_json_schema()
    properties = schema["properties"]

    assert properties["batch_result"]["$ref"].endswith(
        "IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchResult"
    )
    assert properties["diagnostics"]["$ref"].endswith(
        "IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchDiagnostics"
    )
    assert properties["occurrence_projection"]["$ref"].endswith(
        "IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchOccurrenceProjection"
    )
    assert properties["validation_response"]["$ref"].endswith(
        "IntelligenceComparisonArchiveIntegrityReportExportImportSummaryBatchPipelineVerificationResponse"
    )
    assert schema["additionalProperties"] is False
