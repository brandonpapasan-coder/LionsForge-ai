"""Deterministic verification receipts for validated verification-receipt manifests."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest import (
    validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest,
)

_RECEIPT_SCHEMA = (
    "lionsforge.internal-alpha-intelligence-comparison-archive-receipt-manifest-"
    "bundle-receipt-ledger-receipt-manifest-verification-receipt-manifest-verification-receipt"
)
_RECEIPT_KEYS = {
    "schema",
    "schema_version",
    "verification_receipt_manifest_sha256",
    "entry_count",
    "verification_state",
    "interpretation_notice",
    "verification_receipt_manifest_verification_receipt_sha256",
}
_NOTICE = (
    "This receipt proves deterministic bounded verification-receipt manifest verification only "
    "and does not infer causality or authorize any release transition."
)
_BODY_FIELDS = (
    "schema",
    "schema_version",
    "verification_receipt_manifest_sha256",
    "entry_count",
    "verification_state",
    "interpretation_notice",
)
_DIGEST_FINDING = "verification receipt manifest verification receipt digest mismatch"
_CANONICAL_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _is_canonical_sha256(value: object) -> bool:
    return isinstance(value, str) and _CANONICAL_SHA256.fullmatch(value) is not None


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
        "verification_receipt_manifest_sha256": manifest[
            "verification_receipt_manifest_sha256"
        ],
        "entry_count": manifest["entry_count"],
        "verification_state": "VERIFIED",
        "interpretation_notice": _NOTICE,
    }


def build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt(
    manifest: dict[str, Any],
) -> dict[str, Any]:
    """Issue one compact receipt only for a fully valid verification-receipt manifest."""
    findings = validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest(
        manifest
    )
    if findings:
        raise ValueError("invalid verification receipt manifest: " + "; ".join(findings))
    body = _receipt_body(manifest)
    return {
        **body,
        "verification_receipt_manifest_verification_receipt_sha256": hashlib.sha256(
            _canonical_bytes(body)
        ).hexdigest(),
    }


def validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt(
    receipt: dict[str, Any],
    manifest: dict[str, Any],
) -> list[str]:
    """Validate source integrity and the receipt's exact manifest binding fail closed."""
    findings = validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest(
        manifest
    )
    if not isinstance(receipt, dict):
        findings.append("verification receipt manifest verification receipt must be an object")
        return findings

    if set(receipt) != _RECEIPT_KEYS:
        findings.append("verification receipt manifest verification receipt keys invalid")

    try:
        expected_body = _receipt_body(manifest)
    except (KeyError, TypeError, ValueError):
        findings.append("verification receipt manifest verification receipt binding invalid")
        return findings

    if receipt.get("schema") != _RECEIPT_SCHEMA:
        findings.append("verification receipt manifest verification receipt schema mismatch")

    schema_version = receipt.get("schema_version")
    if type(schema_version) is not int or schema_version != 1:
        findings.append(
            "verification receipt manifest verification receipt schema version mismatch"
        )

    submitted_manifest_digest = receipt.get("verification_receipt_manifest_sha256")
    if not _is_canonical_sha256(submitted_manifest_digest):
        findings.append(
            "verification receipt manifest verification receipt verification_receipt_manifest_sha256 invalid"
        )
    elif submitted_manifest_digest != expected_body["verification_receipt_manifest_sha256"]:
        findings.append(
            "verification receipt manifest verification receipt verification_receipt_manifest_sha256 mismatch"
        )

    entry_count = receipt.get("entry_count")
    if type(entry_count) is not int or entry_count < 0:
        findings.append("verification receipt manifest verification receipt entry_count invalid")
    elif entry_count != expected_body["entry_count"]:
        findings.append("verification receipt manifest verification receipt entry_count mismatch")

    for field in ("verification_state", "interpretation_notice"):
        if receipt.get(field) != expected_body[field]:
            findings.append(
                f"verification receipt manifest verification receipt {field} mismatch"
            )

    submitted_body = {field: receipt.get(field) for field in _BODY_FIELDS}
    stored_digest = receipt.get(
        "verification_receipt_manifest_verification_receipt_sha256"
    )
    try:
        submitted_digest = hashlib.sha256(_canonical_bytes(submitted_body)).hexdigest()
        expected_digest = hashlib.sha256(_canonical_bytes(expected_body)).hexdigest()
    except (TypeError, ValueError):
        findings.append("verification receipt manifest verification receipt payload invalid")
        return findings

    if not _is_canonical_sha256(stored_digest):
        findings.append("verification receipt manifest verification receipt digest invalid")
    elif stored_digest != submitted_digest or stored_digest != expected_digest:
        findings.append(_DIGEST_FINDING)
    return findings
