"""Deterministic integrity reports for verified comparison-archive receipt chains."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt import (
    validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt,
)

_REPORT_SCHEMA = "lionsforge.internal-alpha-intelligence-comparison-archive-integrity-report"
_NOTICE = (
    "This report summarizes deterministic receipt-chain integrity only and does not infer "
    "causality or authorize any release transition."
)
_REPORT_KEYS = {
    "schema",
    "schema_version",
    "source_manifest_sha256",
    "source_receipt_sha256",
    "verified_entry_count",
    "integrity_state",
    "finding_count",
    "interpretation_notice",
    "integrity_report_sha256",
}
_BODY_FIELDS = (
    "schema",
    "schema_version",
    "source_manifest_sha256",
    "source_receipt_sha256",
    "verified_entry_count",
    "integrity_state",
    "finding_count",
    "interpretation_notice",
)
_DIGEST_FINDING = "integrity report digest mismatch"


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _report_body(receipt: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": _REPORT_SCHEMA,
        "schema_version": 1,
        "source_manifest_sha256": manifest["verification_receipt_manifest_sha256"],
        "source_receipt_sha256": receipt[
            "verification_receipt_manifest_verification_receipt_sha256"
        ],
        "verified_entry_count": manifest["entry_count"],
        "integrity_state": "VERIFIED",
        "finding_count": 0,
        "interpretation_notice": _NOTICE,
    }


def build_intelligence_comparison_archive_integrity_report(
    receipt: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    """Build one compact report only for a fully valid receipt-manifest pair."""
    findings = validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt(
        receipt,
        manifest,
    )
    if findings:
        raise ValueError("invalid comparison archive integrity source: " + "; ".join(findings))
    body = _report_body(receipt, manifest)
    return {
        **body,
        "integrity_report_sha256": hashlib.sha256(_canonical_bytes(body)).hexdigest(),
    }


def validate_intelligence_comparison_archive_integrity_report(
    report: dict[str, Any],
    receipt: dict[str, Any],
    manifest: dict[str, Any],
) -> list[str]:
    """Validate source integrity, exact bindings, shape, and digest fail closed."""
    findings = validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt(
        receipt,
        manifest,
    )
    if not isinstance(report, dict):
        findings.append("integrity report must be an object")
        return findings
    if set(report) != _REPORT_KEYS:
        findings.append("integrity report keys invalid")

    try:
        expected_body = _report_body(receipt, manifest)
    except (KeyError, TypeError, ValueError):
        findings.append("integrity report binding invalid")
        return findings

    for field in _BODY_FIELDS:
        if report.get(field) != expected_body[field]:
            findings.append(f"integrity report {field} mismatch")

    submitted_body = {field: report.get(field) for field in _BODY_FIELDS}
    stored_digest = report.get("integrity_report_sha256")
    try:
        submitted_digest = hashlib.sha256(_canonical_bytes(submitted_body)).hexdigest()
        expected_digest = hashlib.sha256(_canonical_bytes(expected_body)).hexdigest()
    except (TypeError, ValueError):
        findings.append("integrity report payload invalid")
        return findings

    if stored_digest != submitted_digest:
        findings.append(_DIGEST_FINDING)
    if stored_digest != expected_digest and _DIGEST_FINDING not in findings:
        findings.append(_DIGEST_FINDING)
    return findings
