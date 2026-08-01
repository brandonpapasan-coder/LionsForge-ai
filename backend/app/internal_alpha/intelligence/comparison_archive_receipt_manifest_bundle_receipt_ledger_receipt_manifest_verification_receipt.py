"""Deterministic verification receipts for validated ledger-receipt manifests."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest import (
    validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest,
)

_RECEIPT_SCHEMA = (
    "lionsforge.internal-alpha-intelligence-comparison-archive-receipt-manifest-"
    "bundle-receipt-ledger-receipt-manifest-verification-receipt"
)
_RECEIPT_KEYS = {
    "schema",
    "schema_version",
    "manifest_sha256",
    "entry_count",
    "verification_state",
    "interpretation_notice",
    "manifest_verification_receipt_sha256",
}
_NOTICE = (
    "This receipt proves deterministic bounded ledger-receipt manifest verification only and "
    "does not infer causality or authorize any release transition."
)
_BODY_FIELDS = (
    "schema",
    "schema_version",
    "manifest_sha256",
    "entry_count",
    "verification_state",
    "interpretation_notice",
)
_DIGEST_FINDING = "ledger receipt manifest verification receipt digest mismatch"


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _receipt_body(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": _RECEIPT_SCHEMA,
        "schema_version": 1,
        "manifest_sha256": manifest["manifest_sha256"],
        "entry_count": manifest["entry_count"],
        "verification_state": "VERIFIED",
        "interpretation_notice": _NOTICE,
    }


def build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt(
    manifest: dict[str, Any],
) -> dict[str, Any]:
    """Issue one compact receipt only for a fully valid ledger-receipt manifest."""
    findings = validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest(
        manifest
    )
    if findings:
        raise ValueError("invalid ledger receipt manifest: " + "; ".join(findings))
    body = _receipt_body(manifest)
    return {
        **body,
        "manifest_verification_receipt_sha256": hashlib.sha256(
            _canonical_bytes(body)
        ).hexdigest(),
    }


def validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt(
    receipt: dict[str, Any],
    manifest: dict[str, Any],
) -> list[str]:
    """Validate source integrity and the receipt's exact manifest binding fail closed."""
    findings = validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest(
        manifest
    )
    if not isinstance(receipt, dict):
        findings.append("ledger receipt manifest verification receipt must be an object")
        return findings

    if set(receipt) != _RECEIPT_KEYS:
        findings.append("ledger receipt manifest verification receipt keys invalid")

    try:
        expected_body = _receipt_body(manifest)
    except (KeyError, TypeError, ValueError):
        findings.append("ledger receipt manifest verification receipt binding invalid")
        return findings

    if receipt.get("schema") != _RECEIPT_SCHEMA:
        findings.append("ledger receipt manifest verification receipt schema mismatch")
    if receipt.get("schema_version") != 1:
        findings.append("ledger receipt manifest verification receipt schema version mismatch")
    for field in (
        "manifest_sha256",
        "entry_count",
        "verification_state",
        "interpretation_notice",
    ):
        if receipt.get(field) != expected_body[field]:
            findings.append(
                f"ledger receipt manifest verification receipt {field} mismatch"
            )

    submitted_body = {field: receipt.get(field) for field in _BODY_FIELDS}
    stored_digest = receipt.get("manifest_verification_receipt_sha256")
    try:
        submitted_digest = hashlib.sha256(_canonical_bytes(submitted_body)).hexdigest()
        expected_digest = hashlib.sha256(_canonical_bytes(expected_body)).hexdigest()
    except (TypeError, ValueError):
        findings.append("ledger receipt manifest verification receipt payload invalid")
        return findings

    if stored_digest != submitted_digest:
        findings.append(_DIGEST_FINDING)
    if stored_digest != expected_digest and _DIGEST_FINDING not in findings:
        findings.append(_DIGEST_FINDING)
    return findings
