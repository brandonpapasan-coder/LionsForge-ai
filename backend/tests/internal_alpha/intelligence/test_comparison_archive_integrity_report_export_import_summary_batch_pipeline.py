from app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary_batch_pipeline import (
    build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline,
)


def test_batch_pipeline_composes_canonical_artifacts(monkeypatch):
    calls = []
    summaries = [{"summary": 1}]
    batch_result = {"batch": True}
    diagnostics = {"diagnostics": True}
    occurrence_projection = {"occurrences": True}

    def fake_batch(value):
        calls.append(("batch", value))
        return batch_result

    def fake_diagnostics(value, submitted_batch_result):
        calls.append(("diagnostics", value, submitted_batch_result))
        return diagnostics

    def fake_occurrences(value, submitted_batch_result, submitted_diagnostics):
        calls.append(
            (
                "occurrences",
                value,
                submitted_batch_result,
                submitted_diagnostics,
            )
        )
        return occurrence_projection

    module = (
        "app.internal_alpha.intelligence."
        "comparison_archive_integrity_report_export_import_summary_batch_pipeline"
    )
    monkeypatch.setattr(
        f"{module}.validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch",
        fake_batch,
    )
    monkeypatch.setattr(
        f"{module}.build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics",
        fake_diagnostics,
    )
    monkeypatch.setattr(
        f"{module}.build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences",
        fake_occurrences,
    )

    result = build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline(
        summaries
    )

    assert calls == [
        ("batch", summaries),
        ("diagnostics", summaries, batch_result),
        ("occurrences", summaries, batch_result, diagnostics),
    ]
    assert result == {
        "batch_result": batch_result,
        "diagnostics": diagnostics,
        "occurrence_projection": occurrence_projection,
        "interpretation_notice": (
            "The batch pipeline composes bounded deterministic transport-integrity "
            "artifacts only. It does not authorize any release transition."
        ),
    }


def test_batch_pipeline_propagates_batch_validation_failure(monkeypatch):
    module = (
        "app.internal_alpha.intelligence."
        "comparison_archive_integrity_report_export_import_summary_batch_pipeline"
    )

    def fail(_summaries):
        raise ValueError("invalid batch")

    monkeypatch.setattr(
        f"{module}.validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch",
        fail,
    )

    try:
        build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline(
            []
        )
    except ValueError as exc:
        assert str(exc) == "invalid batch"
    else:
        raise AssertionError("expected batch validation failure")


def test_batch_pipeline_stops_before_occurrences_when_diagnostics_fail(monkeypatch):
    module = (
        "app.internal_alpha.intelligence."
        "comparison_archive_integrity_report_export_import_summary_batch_pipeline"
    )
    occurrence_called = False

    monkeypatch.setattr(
        f"{module}.validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch",
        lambda summaries: {"batch": True},
    )

    def fail_diagnostics(summaries, batch_result):
        raise ValueError("invalid diagnostics source")

    def record_occurrences(summaries, batch_result, diagnostics):
        nonlocal occurrence_called
        occurrence_called = True
        return {}

    monkeypatch.setattr(
        f"{module}.build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostics",
        fail_diagnostics,
    )
    monkeypatch.setattr(
        f"{module}.build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences",
        record_occurrences,
    )

    try:
        build_intelligence_comparison_archive_integrity_report_export_import_summary_batch_pipeline(
            [{}]
        )
    except ValueError as exc:
        assert str(exc) == "invalid diagnostics source"
    else:
        raise AssertionError("expected diagnostics failure")

    assert occurrence_called is False
