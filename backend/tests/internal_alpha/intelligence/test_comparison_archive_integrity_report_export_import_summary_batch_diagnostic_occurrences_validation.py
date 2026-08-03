from app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences_validation import (
    validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences,
)


def _expected_projection() -> dict:
    return {
        "summary_count": 3,
        "finding_count": 3,
        "distinct_finding_count": 2,
        "occurrences": [
            {
                "finding": "a",
                "occurrence_count": 2,
                "affected_summary_count": 2,
                "summary_indexes": [0, 2],
            },
            {
                "finding": "z",
                "occurrence_count": 1,
                "affected_summary_count": 1,
                "summary_indexes": [0],
            },
        ],
        "interpretation_notice": (
            "Diagnostic occurrences locate validated transport-integrity findings only. "
            "They do not authorize any release transition."
        ),
    }


def _inputs() -> tuple[list[dict], dict, dict]:
    summaries = [{}, {}, {}]
    batch_result = {
        "summary_count": 3,
        "valid_count": 1,
        "invalid_count": 2,
        "finding_count": 3,
        "results": [
            {"index": 0, "valid": False, "findings": ["z", "a"]},
            {"index": 1, "valid": True, "findings": []},
            {"index": 2, "valid": False, "findings": ["a"]},
        ],
        "interpretation_notice": "batch",
    }
    diagnostics = {
        "summary_count": 3,
        "invalid_summary_count": 2,
        "invalid_indexes": [0, 2],
        "distinct_finding_count": 2,
        "finding_count": 3,
        "finding_frequencies": [
            {"finding": "a", "count": 2},
            {"finding": "z", "count": 1},
        ],
        "interpretation_notice": "diagnostics",
    }
    return summaries, batch_result, diagnostics


def test_occurrence_projection_validation_accepts_exact_recomputation(monkeypatch):
    expected = _expected_projection()
    monkeypatch.setattr(
        "app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences_validation.build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences",
        lambda summaries, batch_result, diagnostics: expected,
    )
    summaries, batch_result, diagnostics = _inputs()
    assert validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences(
        summaries, batch_result, diagnostics, expected
    ) == []


def test_occurrence_projection_validation_rejects_top_level_shape(monkeypatch):
    expected = _expected_projection()
    monkeypatch.setattr(
        "app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences_validation.build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences",
        lambda summaries, batch_result, diagnostics: expected,
    )
    submitted = {**expected, "extra": True}
    summaries, batch_result, diagnostics = _inputs()
    findings = validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences(
        summaries, batch_result, diagnostics, submitted
    )
    assert "occurrence projection keys do not match the canonical shape" in findings


def test_occurrence_projection_validation_rejects_nested_shape(monkeypatch):
    expected = _expected_projection()
    monkeypatch.setattr(
        "app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences_validation.build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences",
        lambda summaries, batch_result, diagnostics: expected,
    )
    submitted = {**expected, "occurrences": [{**expected["occurrences"][0], "extra": True}, expected["occurrences"][1]]}
    summaries, batch_result, diagnostics = _inputs()
    findings = validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences(
        summaries, batch_result, diagnostics, submitted
    )
    assert "occurrences[0] keys do not match the canonical shape" in findings
    assert "occurrences does not match deterministic recomputation" in findings


def test_occurrence_projection_validation_rejects_count_and_index_tampering(monkeypatch):
    expected = _expected_projection()
    monkeypatch.setattr(
        "app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences_validation.build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences",
        lambda summaries, batch_result, diagnostics: expected,
    )
    tampered_occurrence = {**expected["occurrences"][0], "occurrence_count": 9, "summary_indexes": [2]}
    submitted = {**expected, "occurrences": [tampered_occurrence, expected["occurrences"][1]]}
    summaries, batch_result, diagnostics = _inputs()
    findings = validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences(
        summaries, batch_result, diagnostics, submitted
    )
    assert "occurrences does not match deterministic recomputation" in findings


def test_occurrence_projection_validation_preserves_invalid_source_findings(monkeypatch):
    monkeypatch.setattr(
        "app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences_validation.build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences",
        lambda summaries, batch_result, diagnostics: (_ for _ in ()).throw(ValueError("invalid diagnostics")),
    )
    summaries, batch_result, diagnostics = _inputs()
    assert validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences(
        summaries, batch_result, diagnostics, {}
    ) == ["invalid diagnostics"]


def test_occurrence_projection_validation_rejects_non_object():
    summaries, batch_result, diagnostics = _inputs()
    assert validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences(
        summaries, batch_result, diagnostics, []
    ) == ["occurrence projection must be a JSON object"]
