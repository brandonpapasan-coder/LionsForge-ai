"""Portable deterministic export bundles for comparison-archive integrity reports."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .comparison_archive_integrity_report import (
    validate_intelligence_comparison_archive_integrity_report,
)

_BUNDLE_SCHEMA = "lionsforge.internal-alpha-intelligence-comparison-archive-integrity-report-export-bundle"
_NOTICE = (
    "This bundle packages deterministic receipt-chain integrity evidence for offline "
    "verification only and does not authorize any release transition."
)
_BUNDLE_KEYS = {
    "schema",
    "schema_version",
    "report",
    "receipt",
    "manifest",
    "interpretation_notice",
    "export_bundle_sha256",
}
_BODY_FIELDS = (
    "schema",
    "schema_version",
    "report",
    "receipt",
    "manifest",
    "interpretation_notice",
)
_DIGEST_FINDING = "integrity report export bundle digest mismatch"
_MAX_EXPORT_BYTES = 1_000_000


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _bundle_body(
    report: dict[str, Any],
    receipt: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": _BUNDLE_SCHEMA,
        "schema_version": 1,
        "report": report,
        "receipt": receipt,
        "manifest": manifest,
        "interpretation_notice": _NOTICE,
    }


def build_intelligence_comparison_archive_integrity_report_export_bundle(
    report: dict[str, Any],
    receipt: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    """Build one portable bundle only for a fully valid report and source chain."""
    findings = validate_intelligence_comparison_archive_integrity_report(
        report,
        receipt,
        manifest,
    )
    if findings:
        raise ValueError("invalid comparison archive integrity export source: " + "; ".join(findings))
    body = _bundle_body(report, receipt, manifest)
    return {
        **body,
        "export_bundle_sha256": hashlib.sha256(_canonical_bytes(body)).hexdigest(),
    }


def validate_intelligence_comparison_archive_integrity_report_export_bundle(
    bundle: dict[str, Any],
) -> list[str]:
    """Validate exact nested evidence, strict shape, source chain, and bundle digest."""
    findings: list[str] = []
    if not isinstance(bundle, dict):
        return ["integrity report export bundle must be an object"]
    if set(bundle) != _BUNDLE_KEYS:
        findings.append("integrity report export bundle keys invalid")

    report = bundle.get("report")
    receipt = bundle.get("receipt")
    manifest = bundle.get("manifest")
    if not isinstance(report, dict):
        findings.append("integrity report export bundle report must be an object")
    if not isinstance(receipt, dict):
        findings.append("integrity report export bundle receipt must be an object")
    if not isinstance(manifest, dict):
        findings.append("integrity report export bundle manifest must be an object")
    if not isinstance(report, dict) or not isinstance(receipt, dict) or not isinstance(manifest, dict):
        return findings

    findings.extend(
        validate_intelligence_comparison_archive_integrity_report(
            report,
            receipt,
            manifest,
        )
    )

    expected_body = _bundle_body(report, receipt, manifest)
    for field in ("schema", "schema_version", "interpretation_notice"):
        if bundle.get(field) != expected_body[field]:
            findings.append(f"integrity report export bundle {field} mismatch")

    submitted_body = {field: bundle.get(field) for field in _BODY_FIELDS}
    stored_digest = bundle.get("export_bundle_sha256")
    try:
        submitted_digest = hashlib.sha256(_canonical_bytes(submitted_body)).hexdigest()
        expected_digest = hashlib.sha256(_canonical_bytes(expected_body)).hexdigest()
    except (TypeError, ValueError):
        findings.append("integrity report export bundle payload invalid")
        return findings

    if stored_digest != submitted_digest:
        findings.append(_DIGEST_FINDING)
    if stored_digest != expected_digest and _DIGEST_FINDING not in findings:
        findings.append(_DIGEST_FINDING)
    return findings


def serialize_intelligence_comparison_archive_integrity_report_export_bundle(
    bundle: dict[str, Any],
) -> bytes:
    """Serialize one valid bundle to deterministic UTF-8 JSON bytes."""
    findings = validate_intelligence_comparison_archive_integrity_report_export_bundle(bundle)
    if findings:
        raise ValueError("invalid comparison archive integrity export bundle: " + "; ".join(findings))
    payload = _canonical_bytes(bundle)
    if len(payload) > _MAX_EXPORT_BYTES:
        raise ValueError("comparison archive integrity export bundle exceeds byte limit")
    return payload


def deserialize_intelligence_comparison_archive_integrity_report_export_bundle(
    payload: bytes,
) -> dict[str, Any]:
    """Parse bounded UTF-8 JSON bytes and return only a fully valid bundle."""
    if not isinstance(payload, bytes):
        raise TypeError("comparison archive integrity export payload must be bytes")
    if not payload:
        raise ValueError("comparison archive integrity export payload must not be empty")
    if len(payload) > _MAX_EXPORT_BYTES:
        raise ValueError("comparison archive integrity export payload exceeds byte limit")
    try:
        candidate = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("comparison archive integrity export payload is not valid UTF-8 JSON") from exc
    if not isinstance(candidate, dict):
        raise ValueError("comparison archive integrity export payload must contain an object")
    findings = validate_intelligence_comparison_archive_integrity_report_export_bundle(candidate)
    if findings:
        raise ValueError("invalid comparison archive integrity export bundle: " + "; ".join(findings))
    return candidate
