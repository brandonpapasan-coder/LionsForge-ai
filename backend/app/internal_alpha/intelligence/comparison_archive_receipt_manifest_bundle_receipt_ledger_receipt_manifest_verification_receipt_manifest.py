"""Deterministic manifests for validated ledger-receipt manifest verification receipts."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt import (
    validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt,
)

_MANIFEST_SCHEMA = (
    "lionsforge.internal-alpha-intelligence-comparison-archive-receipt-manifest-"
    "bundle-receipt-ledger-receipt-manifest-verification-receipt-manifest"
)
_MANIFEST_KEYS = {
    "schema",
    "schema_version",
    "entry_count",
    "entries",
    "verification_state",
    "interpretation_notice",
    "verification_receipt_manifest_sha256",
}
_ENTRY_KEYS = {"receipt", "manifest"}
_NOTICE = (
    "This manifest proves deterministic bounded verification-receipt collation only and does not "
    "infer causality or authorize any release transition."
)
_MAX_ENTRIES = 100
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


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


def _validated_entry(entry: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if not isinstance(entry, dict) or set(entry) != _ENTRY_KEYS:
        raise ValueError("verification receipt manifest entry keys invalid")
    receipt = entry.get("receipt")
    manifest = entry.get("manifest")
    if not isinstance(receipt, dict) or not isinstance(manifest, dict):
        raise ValueError("verification receipt manifest entry payload invalid")
    findings = validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt(
        receipt,
        manifest,
    )
    if findings:
        raise ValueError("invalid verification receipt manifest entry: " + "; ".join(findings))
    digest = receipt.get("manifest_verification_receipt_sha256")
    if not _is_canonical_sha256(digest):
        raise ValueError("verification receipt manifest entry digest invalid")
    return digest, {"receipt": receipt, "manifest": manifest}


def _manifest_body(entries: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": _MANIFEST_SCHEMA,
        "schema_version": 1,
        "entry_count": len(entries),
        "entries": entries,
        "verification_state": "VERIFIED",
        "interpretation_notice": _NOTICE,
    }


def build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest(
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build one bounded canonically ordered manifest from valid verification receipts."""
    if not isinstance(entries, list) or not 1 <= len(entries) <= _MAX_ENTRIES:
        raise ValueError("verification receipt manifest entries must contain 1 to 100 items")

    validated = [_validated_entry(entry) for entry in entries]
    digests = [digest for digest, _ in validated]
    if len(set(digests)) != len(digests):
        raise ValueError("verification receipt manifest contains duplicate receipts")

    ordered_entries = [entry for _, entry in sorted(validated, key=lambda item: item[0])]
    body = _manifest_body(ordered_entries)
    return {
        **body,
        "verification_receipt_manifest_sha256": hashlib.sha256(
            _canonical_bytes(body)
        ).hexdigest(),
    }


def validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest(
    manifest: dict[str, Any],
) -> list[str]:
    """Validate shape, receipt bindings, uniqueness, ordering, and digest fail closed."""
    if not isinstance(manifest, dict):
        return ["verification receipt manifest must be an object"]

    findings: list[str] = []
    if set(manifest) != _MANIFEST_KEYS:
        findings.append("verification receipt manifest keys invalid")
    if manifest.get("schema") != _MANIFEST_SCHEMA:
        findings.append("verification receipt manifest schema mismatch")
    if type(manifest.get("schema_version")) is not int or manifest.get("schema_version") != 1:
        findings.append("verification receipt manifest schema version mismatch")
    if manifest.get("verification_state") != "VERIFIED":
        findings.append("verification receipt manifest verification state mismatch")
    if manifest.get("interpretation_notice") != _NOTICE:
        findings.append("verification receipt manifest interpretation notice mismatch")

    entries = manifest.get("entries")
    if not isinstance(entries, list) or not 1 <= len(entries) <= _MAX_ENTRIES:
        findings.append("verification receipt manifest entries invalid")
        return findings
    if type(manifest.get("entry_count")) is not int or manifest.get("entry_count") != len(entries):
        findings.append("verification receipt manifest entry count mismatch")

    validated: list[tuple[str, dict[str, Any]]] = []
    for index, entry in enumerate(entries):
        try:
            validated.append(_validated_entry(entry))
        except (KeyError, TypeError, ValueError) as exc:
            findings.append(f"verification receipt manifest entry {index} invalid: {exc}")

    if len(validated) == len(entries):
        digests = [digest for digest, _ in validated]
        if len(set(digests)) != len(digests):
            findings.append("verification receipt manifest contains duplicate receipts")
        if digests != sorted(digests):
            findings.append("verification receipt manifest entries not canonically ordered")

    try:
        body = _manifest_body(entries)
        expected_digest = hashlib.sha256(_canonical_bytes(body)).hexdigest()
    except (TypeError, ValueError):
        findings.append("verification receipt manifest payload invalid")
        return findings

    stored_digest = manifest.get("verification_receipt_manifest_sha256")
    if not _is_canonical_sha256(stored_digest):
        findings.append("verification receipt manifest digest invalid")
    elif stored_digest != expected_digest:
        findings.append("verification receipt manifest digest mismatch")
    return findings
