"""Deterministic receipts for validated archive receipt manifest bundles."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .comparison_archive_receipt_manifest_bundle import (
    validate_intelligence_comparison_archive_receipt_manifest_bundle,
)

_RECEIPT_SCHEMA = (
    "lionsforge.internal-alpha-intelligence-comparison-archive-receipt-manifest-bundle-receipt"
)
_RECEIPT_KEYS = {
    "schema",
    "schema_version",
    "bundle_sha256",
    "manifest_sha256",
    "receipt_sha256",
    "entry_count",
    "verification_state",
    "interpretation_notice",
    "bundle_receipt_sha256",
}
_NOTICE = (
    "This receipt proves deterministic archive receipt manifest bundle verification only and "
    "does not infer causality or authorize any release transition."
)


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _receipt_body(bundle: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": _RECEIPT_SCHEMA,
        "schema_version": 1,
        "bundle_sha256": bundle["bundle_sha256"],
        "manifest_sha256": bundle["manifest_sha256"],
        "receipt_sha256": bundle["receipt_sha256"],
        "entry_count": bundle["entry_count"],
        "verification_state": "VERIFIED",
        "interpretation_notice": _NOTICE,
    }


def build_intelligence_comparison_archive_receipt_manifest_bundle_receipt(
    bundle: dict[str, Any],
) -> dict[str, Any]:
    """Issue one compact receipt only for a fully valid manifest bundle."""
    findings = validate_intelligence_comparison_archive_receipt_manifest_bundle(bundle)
    if findings:
        raise ValueError("invalid comparison archive receipt manifest bundle: " + "; ".join(findings))
    body = _receipt_body(bundle)
    return {
        **body,
        "bundle_receipt_sha256": hashlib.sha256(_canonical_bytes(body)).hexdigest(),
    }


def validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt(
    receipt: dict[str, Any],
    bundle: dict[str, Any],
) -> list[str]:
    """Validate bundle integrity and the receipt's exact bundle binding fail closed."""
    findings = validate_intelligence_comparison_archive_receipt_manifest_bundle(bundle)
    if not isinstance(receipt, dict):
        findings.append("comparison archive receipt manifest bundle receipt must be an object")
        return findings

    if set(receipt) != _RECEIPT_KEYS:
        findings.append("comparison archive receipt manifest bundle receipt keys invalid")

    try:
        expected_body = _receipt_body(bundle)
    except (KeyError, TypeError, ValueError):
        findings.append("comparison archive receipt manifest bundle receipt binding invalid")
        return findings

    if receipt.get("schema") != _RECEIPT_SCHEMA:
        findings.append("comparison archive receipt manifest bundle receipt schema mismatch")
    if receipt.get("schema_version") != 1:
        findings.append("comparison archive receipt manifest bundle receipt schema version mismatch")
    for field in (
        "bundle_sha256",
        "manifest_sha256",
        "receipt_sha256",
        "entry_count",
        "verification_state",
        "interpretation_notice",
    ):
        if receipt.get(field) != expected_body[field]:
            findings.append(f"comparison archive receipt manifest bundle receipt {field} mismatch")

    expected_digest = hashlib.sha256(_canonical_bytes(expected_body)).hexdigest()
    if receipt.get("bundle_receipt_sha256") != expected_digest:
        findings.append("comparison archive receipt manifest bundle receipt digest mismatch")
    return findings
