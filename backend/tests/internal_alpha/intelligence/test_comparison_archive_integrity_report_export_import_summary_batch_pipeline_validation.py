from copy import deepcopy

from app.internal_alpha.intelligence import (
    comparison_archive_integrity_report_export_import_summary_batch_pipeline_validation as validation,
)


_CANONICAL = {
    "batch_result": {"valid": True, "results": []},
    "diagnostics": {"finding_counts": {}},
    "occurrence_projection": {"occurrences": []},
    "interpretation_notice": "bounded notice",
}


def test_pipeline_validation_accepts_exact_recomputation(monkeypatch) -> None:
    summaries = [{"summary": "one"}]
    forwarded = []

    def fake_build(value):
        forwarded.append(value)
        return deepcopy(_CANONICAL)

    monkeypatch.setattr(
        validation,
        "build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline",
        fake_build,
    )

    assert (
        validation.validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline(
            summaries,
            deepcopy(_CANONICAL),
        )
        == []
    )
    assert forwarded == [summaries]


def test_pipeline_validation_rejects_non_object() -> None:
    assert validation.validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline(
        [],
        [],
    ) == ["pipeline must be a JSON object"]


def test_pipeline_validation_rejects_shape_and_artifact_tampering(monkeypatch) -> None:
    monkeypatch.setattr(
        validation,
        "build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline",
        lambda summaries: deepcopy(_CANONICAL),
    )
    submitted = deepcopy(_CANONICAL)
    submitted["unexpected"] = True
    submitted["diagnostics"] = {"finding_counts": {"tampered": 1}}

    findings = validation.validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline(
        [],
        submitted,
    )

    assert findings == [
        "pipeline keys do not match the canonical shape",
        "diagnostics does not match deterministic recomputation",
    ]


def test_pipeline_validation_rejects_types_and_notice_tampering(monkeypatch) -> None:
    monkeypatch.setattr(
        validation,
        "build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline",
        lambda summaries: deepcopy(_CANONICAL),
    )
    submitted = deepcopy(_CANONICAL)
    submitted["batch_result"] = []
    submitted["occurrence_projection"] = "invalid"
    submitted["interpretation_notice"] = 7

    findings = validation.validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline(
        [],
        submitted,
    )

    assert findings == [
        "batch_result must be a JSON object",
        "batch_result does not match deterministic recomputation",
        "occurrence_projection must be a JSON object",
        "occurrence_projection does not match deterministic recomputation",
        "interpretation_notice must be a string",
        "interpretation_notice does not match deterministic recomputation",
    ]
