from app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences_validation_response import (
    validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences_validation_response,
)


_NOTICE = (
    "Occurrence validity proves deterministic recomputation of bounded "
    "transport-integrity location data only. It does not authorize any "
    "release transition."
)


def _validate(monkeypatch, expected_findings, response):
    monkeypatch.setattr(
        "app.internal_alpha.intelligence.comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences_validation_response.validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences",
        lambda summaries, batch_result, diagnostics, occurrence_projection: expected_findings,
    )
    return validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences_validation_response(
        [{}],
        {"batch": True},
        {"diagnostics": True},
        {"occurrences": []},
        response,
    )


def test_validation_response_accepts_exact_valid_recomputation(monkeypatch):
    response = {
        "valid": True,
        "findings": [],
        "interpretation_notice": _NOTICE,
    }
    assert _validate(monkeypatch, [], response) == []


def test_validation_response_accepts_exact_invalid_recomputation(monkeypatch):
    response = {
        "valid": False,
        "findings": ["tampered", "notice mismatch"],
        "interpretation_notice": _NOTICE,
    }
    assert _validate(monkeypatch, ["tampered", "notice mismatch"], response) == []


def test_validation_response_rejects_non_object(monkeypatch):
    assert _validate(monkeypatch, [], []) == [
        "validation response must be a JSON object"
    ]


def test_validation_response_rejects_shape_tampering(monkeypatch):
    response = {
        "valid": True,
        "findings": [],
        "interpretation_notice": _NOTICE,
        "extra": True,
    }
    findings = _validate(monkeypatch, [], response)
    assert "validation response keys do not match the canonical shape" in findings


def test_validation_response_rejects_validity_tampering(monkeypatch):
    response = {
        "valid": True,
        "findings": ["tampered"],
        "interpretation_notice": _NOTICE,
    }
    findings = _validate(monkeypatch, ["tampered"], response)
    assert "valid does not match deterministic recomputation" in findings


def test_validation_response_rejects_finding_order_tampering(monkeypatch):
    response = {
        "valid": False,
        "findings": ["b", "a"],
        "interpretation_notice": _NOTICE,
    }
    findings = _validate(monkeypatch, ["a", "b"], response)
    assert "findings does not match deterministic recomputation" in findings


def test_validation_response_rejects_notice_tampering(monkeypatch):
    response = {
        "valid": True,
        "findings": [],
        "interpretation_notice": "changed",
    }
    findings = _validate(monkeypatch, [], response)
    assert "interpretation_notice does not match deterministic recomputation" in findings


def test_validation_response_rejects_non_boolean_valid(monkeypatch):
    response = {
        "valid": 1,
        "findings": [],
        "interpretation_notice": _NOTICE,
    }
    findings = _validate(monkeypatch, [], response)
    assert "valid must be a boolean" in findings
    assert "valid does not match deterministic recomputation" in findings


def test_validation_response_rejects_non_list_findings(monkeypatch):
    response = {
        "valid": True,
        "findings": "none",
        "interpretation_notice": _NOTICE,
    }
    findings = _validate(monkeypatch, [], response)
    assert "findings must be a list" in findings
    assert "findings does not match deterministic recomputation" in findings


def test_validation_response_rejects_non_string_finding_items(monkeypatch):
    response = {
        "valid": False,
        "findings": [1],
        "interpretation_notice": _NOTICE,
    }
    findings = _validate(monkeypatch, ["1"], response)
    assert "findings must contain only strings" in findings
    assert "findings does not match deterministic recomputation" in findings
