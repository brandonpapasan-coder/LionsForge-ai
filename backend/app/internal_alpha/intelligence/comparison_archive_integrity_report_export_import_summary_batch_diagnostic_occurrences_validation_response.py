"""Fail-closed validation for diagnostic occurrence API responses."""

from __future__ import annotations

from typing import Any

from .comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences_validation import (
    validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences,
)

_EXPECTED_KEYS = {"valid", "findings", "interpretation_notice"}
_NOTICE = (
    "Occurrence validity proves deterministic recomputation of bounded "
    "transport-integrity location data only. It does not authorize any "
    "release transition."
)


def validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences_validation_response(
    summaries: list[dict[str, Any]],
    batch_result: dict[str, Any],
    diagnostics: dict[str, Any],
    occurrence_projection: dict[str, Any],
    response: dict[str, Any],
) -> list[str]:
    """Return deterministic findings for one submitted validation response."""
    findings: list[str] = []
    if not isinstance(response, dict):
        return ["validation response must be a JSON object"]
    if set(response) != _EXPECTED_KEYS:
        findings.append("validation response keys do not match the canonical shape")

    expected_findings = validate_intelligence_comparison_archive_integrity_report_export_import_summary_batch_diagnostic_occurrences(
        summaries,
        batch_result,
        diagnostics,
        occurrence_projection,
    )
    expected = {
        "valid": not expected_findings,
        "findings": expected_findings,
        "interpretation_notice": _NOTICE,
    }

    if not isinstance(response.get("valid"), bool):
        findings.append("valid must be a boolean")
    if not isinstance(response.get("findings"), list):
        findings.append("findings must be a list")
    elif any(not isinstance(item, str) for item in response["findings"]):
        findings.append("findings must contain only strings")

    for key in ("valid", "findings", "interpretation_notice"):
        if response.get(key) != expected[key]:
            findings.append(f"{key} does not match deterministic recomputation")

    return findings
