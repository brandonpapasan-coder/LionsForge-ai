"""Deterministic bounded ledgers for validated manifest bundle receipts."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .comparison_archive_receipt_manifest_bundle_receipt import (
    validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt,
)

_LEDGER_SCHEMA = (
    "lionsforge.internal-alpha-intelligence-comparison-archive-receipt-manifest-"
    "bundle-receipt-ledger"
)
_LEDGER_KEYS = {
    "schema",
    "schema_version",
    "entry_count",
    "entries",
    "verification_state",
    "interpretation_notice",
    "ledger_sha256",
}
_ENTRY_KEYS = {
    "bundle_receipt_sha256",
    "bundle_sha256",
    "manifest_sha256",
    "receipt_sha256",
    "entry_count",
}
_NOTICE = (
    "This ledger proves deterministic bounded receipt collation only and does not infer "
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


def _entry(receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        "bundle_receipt_sha256": receipt["bundle_receipt_sha256"],
        "bundle_sha256": receipt["bundle_sha256"],
        "manifest_sha256": receipt["manifest_sha256"],
        "receipt_sha256": receipt["receipt_sha256"],
        "entry_count": receipt["entry_count"],
    }


def build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger(
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build one stable bounded ledger from exact bundle and receipt pairs."""
    if not isinstance(items, list) or not 1 <= len(items) <= _MAX_ENTRIES:
        raise ValueError("bundle receipt ledger items must contain between 1 and 100 entries")

    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict) or set(item) != {"receipt", "bundle"}:
            raise ValueError("bundle receipt ledger item keys invalid")
        receipt = item["receipt"]
        bundle = item["bundle"]
        findings = validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt(
            receipt,
            bundle,
        )
        if findings:
            raise ValueError("invalid bundle receipt ledger item: " + "; ".join(findings))
        digest = receipt["bundle_receipt_sha256"]
        if digest in seen:
            raise ValueError("duplicate bundle receipt ledger entry")
        seen.add(digest)
        entries.append(_entry(receipt))

    entries.sort(key=lambda entry: entry["bundle_receipt_sha256"])
    body = {
        "schema": _LEDGER_SCHEMA,
        "schema_version": 1,
        "entry_count": len(entries),
        "entries": entries,
        "verification_state": "VERIFIED",
        "interpretation_notice": _NOTICE,
    }
    return {**body, "ledger_sha256": hashlib.sha256(_canonical_bytes(body)).hexdigest()}


def validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger(
    ledger: dict[str, Any],
) -> list[str]:
    """Validate ledger structure, ordering, uniqueness, and digest fail closed."""
    findings: list[str] = []
    if not isinstance(ledger, dict):
        return ["bundle receipt ledger must be an object"]
    if set(ledger) != _LEDGER_KEYS:
        findings.append("bundle receipt ledger keys invalid")
    if ledger.get("schema") != _LEDGER_SCHEMA:
        findings.append("bundle receipt ledger schema mismatch")
    if ledger.get("schema_version") != 1:
        findings.append("bundle receipt ledger schema version mismatch")
    if ledger.get("verification_state") != "VERIFIED":
        findings.append("bundle receipt ledger verification state mismatch")
    if ledger.get("interpretation_notice") != _NOTICE:
        findings.append("bundle receipt ledger interpretation notice mismatch")

    entries = ledger.get("entries")
    if not isinstance(entries, list) or not 1 <= len(entries) <= _MAX_ENTRIES:
        findings.append("bundle receipt ledger entries invalid")
        return findings
    if ledger.get("entry_count") != len(entries):
        findings.append("bundle receipt ledger entry count mismatch")

    digests: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != _ENTRY_KEYS:
            findings.append("bundle receipt ledger entry keys invalid")
            continue
        digest = entry.get("bundle_receipt_sha256")
        if not isinstance(digest, str) or len(digest) != 64:
            findings.append("bundle receipt ledger entry digest invalid")
        else:
            digests.append(digest)
    if len(digests) != len(set(digests)):
        findings.append("bundle receipt ledger duplicate entry")
    if digests != sorted(digests):
        findings.append("bundle receipt ledger ordering invalid")

    body = {key: ledger.get(key) for key in _LEDGER_KEYS if key != "ledger_sha256"}
    try:
        expected_digest = hashlib.sha256(_canonical_bytes(body)).hexdigest()
    except (TypeError, ValueError):
        findings.append("bundle receipt ledger canonicalization invalid")
        return findings
    if ledger.get("ledger_sha256") != expected_digest:
        findings.append("bundle receipt ledger digest mismatch")
    return findings
