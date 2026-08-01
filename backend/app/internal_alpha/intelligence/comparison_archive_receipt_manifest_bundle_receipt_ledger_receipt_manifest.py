"""Deterministic manifests for validated archive bundle-receipt ledger receipts."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt import (
    validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt,
)

_MANIFEST_SCHEMA = (
    "lionsforge.internal-alpha-intelligence-comparison-archive-receipt-manifest-"
    "bundle-receipt-ledger-receipt-manifest"
)
_MANIFEST_KEYS = {
    "schema",
    "schema_version",
    "entry_count",
    "entries",
    "verification_state",
    "interpretation_notice",
    "manifest_sha256",
}
_ENTRY_KEYS = {"receipt", "ledger"}
_NOTICE = (
    "This manifest proves deterministic bounded ledger-receipt collation only and does not infer "
    "causality or authorize any release transition."
)
_MAX_ENTRIES = 100


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _validated_entry(entry: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if not isinstance(entry, dict) or set(entry) != _ENTRY_KEYS:
        raise ValueError("ledger receipt manifest entry keys invalid")
    receipt = entry.get("receipt")
    ledger = entry.get("ledger")
    if not isinstance(receipt, dict) or not isinstance(ledger, dict):
        raise ValueError("ledger receipt manifest entry payload invalid")
    findings = (
        validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt(
            receipt,
            ledger,
        )
    )
    if findings:
        raise ValueError("invalid ledger receipt manifest entry: " + "; ".join(findings))
    digest = receipt.get("ledger_receipt_sha256")
    if not isinstance(digest, str) or len(digest) != 64:
        raise ValueError("ledger receipt manifest entry digest invalid")
    return digest, {"receipt": receipt, "ledger": ledger}


def _manifest_body(entries: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": _MANIFEST_SCHEMA,
        "schema_version": 1,
        "entry_count": len(entries),
        "entries": entries,
        "verification_state": "VERIFIED",
        "interpretation_notice": _NOTICE,
    }


def build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest(
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build one bounded canonically ordered manifest from valid ledger receipts."""
    if not isinstance(entries, list) or not 1 <= len(entries) <= _MAX_ENTRIES:
        raise ValueError("ledger receipt manifest entries must contain 1 to 100 items")

    validated = [_validated_entry(entry) for entry in entries]
    digests = [digest for digest, _ in validated]
    if len(set(digests)) != len(digests):
        raise ValueError("ledger receipt manifest contains duplicate receipts")

    ordered_entries = [entry for _, entry in sorted(validated, key=lambda item: item[0])]
    body = _manifest_body(ordered_entries)
    return {
        **body,
        "manifest_sha256": hashlib.sha256(_canonical_bytes(body)).hexdigest(),
    }


def validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest(
    manifest: dict[str, Any],
) -> list[str]:
    """Validate shape, receipt chains, uniqueness, ordering, and digest fail closed."""
    if not isinstance(manifest, dict):
        return ["ledger receipt manifest must be an object"]

    findings: list[str] = []
    if set(manifest) != _MANIFEST_KEYS:
        findings.append("ledger receipt manifest keys invalid")
    if manifest.get("schema") != _MANIFEST_SCHEMA:
        findings.append("ledger receipt manifest schema mismatch")
    if manifest.get("schema_version") != 1:
        findings.append("ledger receipt manifest schema version mismatch")
    if manifest.get("verification_state") != "VERIFIED":
        findings.append("ledger receipt manifest verification state mismatch")
    if manifest.get("interpretation_notice") != _NOTICE:
        findings.append("ledger receipt manifest interpretation notice mismatch")

    entries = manifest.get("entries")
    if not isinstance(entries, list) or not 1 <= len(entries) <= _MAX_ENTRIES:
        findings.append("ledger receipt manifest entries invalid")
        return findings
    if manifest.get("entry_count") != len(entries):
        findings.append("ledger receipt manifest entry count mismatch")

    validated: list[tuple[str, dict[str, Any]]] = []
    for index, entry in enumerate(entries):
        try:
            validated.append(_validated_entry(entry))
        except (KeyError, TypeError, ValueError) as exc:
            findings.append(f"ledger receipt manifest entry {index} invalid: {exc}")

    if len(validated) == len(entries):
        digests = [digest for digest, _ in validated]
        if len(set(digests)) != len(digests):
            findings.append("ledger receipt manifest contains duplicate receipts")
        if digests != sorted(digests):
            findings.append("ledger receipt manifest entries not canonically ordered")

    try:
        body = _manifest_body(entries)
        expected_digest = hashlib.sha256(_canonical_bytes(body)).hexdigest()
    except (TypeError, ValueError):
        findings.append("ledger receipt manifest payload invalid")
        return findings
    if manifest.get("manifest_sha256") != expected_digest:
        findings.append("ledger receipt manifest digest mismatch")
    return findings
