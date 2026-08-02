"""Fail-closed validation for deterministic integrity-report bundle import summaries."""

from __future__ import annotations

import hashlib
from typing import Any

from .comparison_archive_integrity_report_export_bundle import (
    serialize_intelligence_comparison_archive_integrity_report_export_bundle,
    validate_intelligence_comparison_archive_integrity_report_export_bundle,
)

_SUMMARY_KEYS = {
    "bundle",
    "canonical_byte_count",
    "canonical_payload_sha256",
    "export_bundle_sha256",
    "interpretation_notice",
}
_SUMMARY_NOTICE = (
    "Import metadata identifies exact canonical bytes and embedded bundle integrity only. "
    "It does not authorize any release transition."
)


def validate_intelligence_comparison_archive_integrity_report_export_import_summary(
    summary: dict[str, Any],
) -> list[str]:
    """Validate strict summary shape and reconstruct all transport metadata from its bundle."""
    if not isinstance(summary, dict):
        return ["integrity report export import summary must be an object"]

    findings: list[str] = []
    if set(summary) != _SUMMARY_KEYS:
        findings.append("integrity report export import summary keys invalid")

    bundle = summary.get("bundle")
    if not isinstance(bundle, dict):
        findings.append("integrity report export import summary bundle must be an object")
        return findings

    bundle_findings = validate_intelligence_comparison_archive_integrity_report_export_bundle(bundle)
    findings.extend(bundle_findings)
    if bundle_findings:
        return findings

    try:
        canonical_payload = serialize_intelligence_comparison_archive_integrity_report_export_bundle(
            bundle
        )
    except (TypeError, ValueError):
        findings.append("integrity report export import summary bundle serialization failed")
        return findings

    if type(summary.get("canonical_byte_count")) is not int:
        findings.append("integrity report export import summary canonical_byte_count invalid")
    elif summary["canonical_byte_count"] != len(canonical_payload):
        findings.append("integrity report export import summary canonical_byte_count mismatch")

    expected_payload_digest = hashlib.sha256(canonical_payload).hexdigest()
    if summary.get("canonical_payload_sha256") != expected_payload_digest:
        findings.append("integrity report export import summary canonical_payload_sha256 mismatch")

    if summary.get("export_bundle_sha256") != bundle.get("export_bundle_sha256"):
        findings.append("integrity report export import summary export_bundle_sha256 mismatch")

    if summary.get("interpretation_notice") != _SUMMARY_NOTICE:
        findings.append("integrity report export import summary interpretation_notice mismatch")

    return findings
