"""Deterministic verification receipts for validated ledger-receipt manifests."""

from __future__ import annotations

import hashlib
import json
import re
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
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_DIGEST_FINDING = "ledger receipt manifest verification receipt digest mismatch"
_DIGEST_INVALID_FINDING = "ledger receipt manifest verification receipt digest invalid"


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _is_canonical_sha256(value: Any) -> bool:
    return isinstance(value, str) and _SHA256_PATTERN.fullmatch(value) is not None


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
    if type(receipt.get("schema_version")) is not int or receipt.get("schema_version") != 1:
        findings.append("ledger receipt manifest verification receipt schema version mismatch")

    submitted_manifest_sha256 = receipt.get("manifest_sha256")
    if not _is_canonical_sha256(submitted_manifest_sha256):
        findings.append("ledger receipt manifest verification receipt manifest_sha256 invalid")
    elif submitted_manifest_sha256 != expected_body["manifest_sha256"]:
        findings.append("ledger receipt manifest verification receipt manifest_sha256 mismatch")

    submitted_entry_count = receipt.get("entry_count")
    if type(submitted_entry_count) is not int:
        findings.append("ledger receipt manifest verification receipt entry_count invalid")
    elif submitted_entry_count != expected_body["entry_count"]:
        findings.append("ledger receipt manifest verification receipt entry_count mismatch")

    for field in ("verification_state", "interpretation_notice"):
        if receipt.get(field) != expected_body[field]:
            findings.append(
                f"ledger receipt manifest verification receipt {field} mismatch"
            )

    submitted_body = {field: receipt.get(field) for field in _BODY_FIELDS}
    stored_digest = receipt.get("manifest_verification_receipt_sha256")
    if not _is_canonical_sha256(stored_digest):
        findings.append(_DIGEST_INVALID_FINDING)
        return findings

    try:
        submitted_digest = hashlib.sha256(_canonical_bytes(submitted_body)).hexdigest()
        expected_digest = hashlib.sha256(_canonical_bytes(expected_body)).hexdigest()
    except (TypeError, ValueError):
        findings.append("ledger receipt manifest verification receipt payload invalid")
        return findings

    if stored_digest != submitted_digest or stored_digest != expected_digest:
        findings.append(_DIGEST_FINDING)
    return findings
