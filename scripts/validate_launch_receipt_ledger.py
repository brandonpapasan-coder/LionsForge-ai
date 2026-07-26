#!/usr/bin/env python3
"""Validate a LionsForge AI launch receipt ledger.

The ledger orders canonical launch evidence-chain receipts for audit purposes only.
It does not verify live evidence or authorize deployment, beta, payments, public
registration, or general availability.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "lionsforge.launch-receipt-ledger"
VERSION = 1
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
ALLOWED_STATUS = {"current", "superseded", "revoked"}
TOP_FIELDS = {"schema", "schema_version", "entries"}
ENTRY_FIELDS = {
    "sequence",
    "receipt_sha256",
    "predecessor_sha256",
    "release_sha",
    "recorded_at",
    "status",
    "reason",
    "owner",
}
SENSITIVE_PATTERNS = (
    re.compile(
        r"(?i)[\"']?\b(?:api[_-]?key|access[_-]?token|secret|password)\b[\"']?\s*[:=]\s*\S+"
    ),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)
PROHIBITED_TERMS = (
    "private tester identity",
    "answer key",
    "hidden assessment metadata",
    "deletion request contents",
)


@dataclass(frozen=True, order=True)
class Finding:
    code: str
    field: str
    message: str


def _parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        return None
    return parsed


def _receipt_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _receipt_release_sha(path: Path) -> str | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    identity = data.get("identity") if isinstance(data, dict) else None
    value = identity.get("release_sha") if isinstance(identity, dict) else None
    return value if isinstance(value, str) and SHA_RE.fullmatch(value) else None


def _privacy_findings(raw_text: str) -> list[Finding]:
    findings: list[Finding] = []
    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(raw_text):
            findings.append(
                Finding("sensitive-content", "ledger", "Ledger contains apparent credential or secret content")
            )
            break
    lowered = raw_text.lower()
    for term in PROHIBITED_TERMS:
        if term in lowered:
            findings.append(
                Finding("prohibited-content", "ledger", f"Ledger contains prohibited private content marker: {term}")
            )
    return findings


def validate_ledger(data: Any, receipt_paths: list[Path] | None = None) -> list[Finding]:
    findings: list[Finding] = []
    if not isinstance(data, dict):
        return [Finding("invalid-json-shape", "ledger", "Ledger root must be a JSON object")]

    for field in sorted(TOP_FIELDS - set(data)):
        findings.append(Finding("missing-field", field, f"Required ledger field is missing: {field}"))
    for field in sorted(set(data) - TOP_FIELDS):
        findings.append(Finding("unsupported-field", field, f"Unsupported ledger field: {field}"))
    if data.get("schema") != SCHEMA:
        findings.append(Finding("unsupported-schema", "schema", f"Schema must be {SCHEMA}"))
    if data.get("schema_version") != VERSION:
        findings.append(Finding("unsupported-version", "schema_version", f"Schema version must be {VERSION}"))

    entries = data.get("entries")
    if not isinstance(entries, list) or not entries:
        findings.append(Finding("invalid-entries", "entries", "entries must be a non-empty array"))
        return sorted(findings)

    seen_receipts: set[str] = set()
    seen_sequences: set[int] = set()
    seen_releases: set[str] = set()
    current_indexes: list[int] = []
    prior_digest = ""
    prior_time: datetime | None = None

    for index, entry in enumerate(entries):
        prefix = f"entries[{index}]"
        if not isinstance(entry, dict):
            findings.append(Finding("invalid-entry", prefix, "Ledger entry must be a JSON object"))
            continue
        for field in sorted(ENTRY_FIELDS - set(entry)):
            findings.append(Finding("missing-entry-field", f"{prefix}.{field}", f"Entry field is missing: {field}"))
        for field in sorted(set(entry) - ENTRY_FIELDS):
            findings.append(Finding("unsupported-entry-field", f"{prefix}.{field}", f"Unsupported entry field: {field}"))

        sequence = entry.get("sequence")
        expected_sequence = index + 1
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
            findings.append(Finding("invalid-sequence", f"{prefix}.sequence", "sequence must be a positive integer"))
        else:
            if sequence in seen_sequences:
                findings.append(Finding("duplicate-sequence", f"{prefix}.sequence", "sequence values must be unique"))
            seen_sequences.add(sequence)
            if sequence != expected_sequence:
                findings.append(Finding("sequence-gap", f"{prefix}.sequence", f"Expected sequence {expected_sequence}"))

        digest = entry.get("receipt_sha256")
        if not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest):
            findings.append(Finding("invalid-digest", f"{prefix}.receipt_sha256", "receipt_sha256 must be 64 lowercase hexadecimal characters"))
            digest = ""
        elif digest in seen_receipts:
            findings.append(Finding("replayed-receipt", f"{prefix}.receipt_sha256", "Receipt digest must not appear more than once"))
        else:
            seen_receipts.add(digest)

        predecessor = entry.get("predecessor_sha256")
        if index == 0:
            if predecessor not in {"", None}:
                findings.append(Finding("invalid-predecessor", f"{prefix}.predecessor_sha256", "First entry must not have a predecessor"))
        elif predecessor != prior_digest:
            findings.append(Finding("fork-or-gap", f"{prefix}.predecessor_sha256", "Entry must reference the immediately prior receipt digest"))

        release_sha = entry.get("release_sha")
        if not isinstance(release_sha, str) or not SHA_RE.fullmatch(release_sha):
            findings.append(Finding("invalid-release-sha", f"{prefix}.release_sha", "release_sha must be exactly 40 lowercase hexadecimal characters"))
        elif release_sha in seen_releases:
            findings.append(Finding("duplicate-release", f"{prefix}.release_sha", "Each ledger entry must bind a distinct release SHA"))
        else:
            seen_releases.add(release_sha)

        recorded_at = _parse_utc(entry.get("recorded_at"))
        if recorded_at is None:
            findings.append(Finding("invalid-timestamp", f"{prefix}.recorded_at", "recorded_at must be an ISO-8601 UTC timestamp"))
        elif prior_time is not None and recorded_at <= prior_time:
            findings.append(Finding("timestamp-regression", f"{prefix}.recorded_at", "recorded_at values must be strictly increasing"))
        if recorded_at is not None:
            prior_time = recorded_at

        status = entry.get("status")
        if status not in ALLOWED_STATUS:
            findings.append(Finding("invalid-status", f"{prefix}.status", "status must be current, superseded, or revoked"))
        elif status == "current":
            current_indexes.append(index)
            if index != len(entries) - 1:
                findings.append(Finding("stale-current", f"{prefix}.status", "Only the final ledger entry may be current"))
        elif index == len(entries) - 1:
            findings.append(Finding("final-not-current", f"{prefix}.status", "The final ledger entry must be current"))

        reason = entry.get("reason")
        owner = entry.get("owner")
        if status in {"superseded", "revoked"}:
            if not isinstance(reason, str) or not reason.strip():
                findings.append(Finding("missing-reason", f"{prefix}.reason", "Superseded or revoked entries require a reason"))
            if not isinstance(owner, str) or not owner.strip():
                findings.append(Finding("missing-owner", f"{prefix}.owner", "Superseded or revoked entries require an owner"))
        else:
            if reason not in {"", None}:
                findings.append(Finding("unexpected-reason", f"{prefix}.reason", "Current entry reason must be blank"))
            if not isinstance(owner, str) or not owner.strip():
                findings.append(Finding("missing-owner", f"{prefix}.owner", "Current entry requires an owner"))

        prior_digest = digest

    if len(current_indexes) != 1:
        findings.append(Finding("current-count", "entries", "Ledger must contain exactly one current entry"))

    if receipt_paths is not None:
        if len(receipt_paths) != len(entries):
            findings.append(Finding("receipt-count", "receipts", "Receipt path count must match ledger entry count"))
        else:
            for index, (entry, path) in enumerate(zip(entries, receipt_paths, strict=True)):
                prefix = f"entries[{index}]"
                try:
                    actual_digest = _receipt_digest(path)
                except OSError as exc:
                    findings.append(Finding("receipt-unreadable", f"receipts[{index}]", str(exc)))
                    continue
                if isinstance(entry, dict) and entry.get("receipt_sha256") != actual_digest:
                    findings.append(Finding("receipt-drift", f"{prefix}.receipt_sha256", "Receipt file does not match ledger digest"))
                release_sha = _receipt_release_sha(path)
                if release_sha is None:
                    findings.append(Finding("receipt-invalid", f"receipts[{index}]", "Receipt file is not valid JSON with a canonical release SHA"))
                elif isinstance(entry, dict) and entry.get("release_sha") != release_sha:
                    findings.append(Finding("release-drift", f"{prefix}.release_sha", "Receipt release identity does not match ledger"))

    return sorted(findings)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("receipts", nargs="*", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        raw_text = args.ledger.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR ledger-unreadable: {exc}", file=sys.stderr)
        return 1
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        print(f"ERROR malformed-json: {exc}")
        return 1

    findings = _privacy_findings(raw_text)
    findings.extend(validate_ledger(data, args.receipts or None))
    findings = sorted(set(findings))
    if findings:
        for finding in findings:
            print(f"ERROR {finding.code} [{finding.field}]: {finding.message}")
        print(f"INVALID: {len(findings)} finding(s)")
        return 1
    print("VALID: launch receipt ledger is internally consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
