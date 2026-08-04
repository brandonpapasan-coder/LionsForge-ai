from app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary_batch_pipeline_validation_response import (
    validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline_validation_response,
)


_NOTICE = (
    "Pipeline validity proves deterministic recomputation of bounded "
    "transport-integrity artifacts only. It does not authorize any release transition."
)


def _summaries() -> list[dict]:
    return [{"summary": 1}]


def _pipeline() -> dict:
    return {
        "batch_result": {},
        "diagnostics": {},
        "occurrence_projection": {},
        "interpretation_notice": "bounded",
    }


def test_validation_response_accepts_exact_valid_recomputation(monkeypatch):
    monkeypatch.setattr(
        "app.internal_alpha.intelligence."
        "comparison_archive_integrity_report_export_import_summary_batch_pipeline_validation_response."
        "validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline",
        lambda summaries, pipeline: [],
    )

    assert validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline_validation_response(
        _summaries(),
        _pipeline(),
        {"valid": True, "findings": [], "interpretation_notice": _NOTICE},
    ) == []


def test_validation_response_accepts_exact_invalid_recomputation(monkeypatch):
    expected_findings = ["pipeline keys do not match the canonical shape"]
    monkeypatch.setattr(
        "app.internal_alpha.intelligence."
        "comparison_archive_integrity_report_export_import_summary_batch_pipeline_validation_response."
        "validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline",
        lambda summaries, pipeline: expected_findings,
    )

    assert validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline_validation_response(
        _summaries(),
        _pipeline(),
        {
            "valid": False,
            "findings": expected_findings,
            "interpretation_notice": _NOTICE,
        },
    ) == []


def test_validation_response_forwards_exact_sources(monkeypatch):
    captured = {}

    def fake_validate(summaries, pipeline):
        captured["summaries"] = summaries
        captured["pipeline"] = pipeline
        return []

    monkeypatch.setattr(
        "app.internal_alpha.intelligence."
        "comparison_archive_integrity_report_export_import_summary_batch_pipeline_validation_response."
        "validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline",
        fake_validate,
    )
    summaries = _summaries()
    pipeline = _pipeline()
    validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline_validation_response(
        summaries,
        pipeline,
        {"valid": True, "findings": [], "interpretation_notice": _NOTICE},
    )

    assert captured == {"summaries": summaries, "pipeline": pipeline}


def test_validation_response_rejects_non_object():
    assert validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline_validation_response(
        _summaries(), _pipeline(), []
    ) == ["validation response must be a JSON object"]


def test_validation_response_rejects_shape_tampering(monkeypatch):
    monkeypatch.setattr(
        "app.internal_alpha.intelligence."
        "comparison_archive_integrity_report_export_import_summary_batch_pipeline_validation_response."
        "validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline",
        lambda summaries, pipeline: [],
    )
    findings = validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline_validation_response(
        _summaries(),
        _pipeline(),
        {
            "valid": True,
            "findings": [],
            "interpretation_notice": _NOTICE,
            "unexpected": True,
        },
    )
    assert findings == ["validation response keys do not match the canonical shape"]


def test_validation_response_rejects_type_tampering(monkeypatch):
    monkeypatch.setattr(
        "app.internal_alpha.intelligence."
        "comparison_archive_integrity_report_export_import_summary_batch_pipeline_validation_response."
        "validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline",
        lambda summaries, pipeline: [],
    )
    findings = validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline_validation_response(
        _summaries(),
        _pipeline(),
        {"valid": "yes", "findings": [1], "interpretation_notice": 1},
    )
    assert findings == [
        "valid must be a boolean",
        "findings must contain only strings",
        "interpretation_notice must be a string",
        "valid does not match deterministic recomputation",
        "findings does not match deterministic recomputation",
        "interpretation_notice does not match deterministic recomputation",
    ]


def test_validation_response_rejects_validity_findings_and_notice_tampering(monkeypatch):
    expected_findings = ["pipeline keys do not match the canonical shape"]
    monkeypatch.setattr(
        "app.internal_alpha.intelligence."
        "comparison_archive_integrity_report_export_import_summary_batch_pipeline_validation_response."
        "validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline",
        lambda summaries, pipeline: expected_findings,
    )
    findings = validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline_validation_response(
        _summaries(),
        _pipeline(),
        {"valid": True, "findings": [], "interpretation_notice": "tampered"},
    )
    assert findings == [
        "valid does not match deterministic recomputation",
        "findings does not match deterministic recomputation",
        "interpretation_notice does not match deterministic recomputation",
    ]
