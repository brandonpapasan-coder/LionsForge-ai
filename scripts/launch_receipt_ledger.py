#!/usr/bin/env python3
"""Validate a LionsForge AI launch receipt ledger.

The ledger proves deterministic ordering and integrity relationships between
non-secret launch evidence-chain receipts. It does not prove live evidence,
deployment state, ownership, freshness, or launch authorization.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECEIPT_VALIDATOR = ROOT / "scripts" / "launch_evidence_chain_receipt.py"
SCHEMA = "lionsforge.launch-receipt-ledger"
VERSION = 1
TOOL_VERSION = "1.0.0"
STATUSES = {"current", "superseded", "revoked"}
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SECRET_RE = re.compile(
    r"(?i)(-----BEGIN [A-Z ]*PRIVATE KEY-----|(?:api[_-]?key|password|passwd|secret|token)\s*[:=]\s*\S+)"
)
PROHIBITED_KEY_RE = re.compile(
    r"(?i)(credential|password|passwd|secret|token|private[_-]?key|tester[_-]?identity|prompt|research[_-]?content|support[_-]?record|deletion[_-]?request|answer[_-]?key|hidden[_-]?assessment)"
)


@dataclass(frozen=True, order=True)
class Finding:
    code: str
    field: str
    message: str


def _load_receipt_validator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("launch_receipt_validator", RECEIPT_VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load receipt validator: {RECEIPT_VALIDATOR}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _parse_utc(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        return None
    return parsed


def _privacy_findings(value: Any, field: str = "ledger") -> list[Finding]:
    findings: list[Finding] = []
    if isinstance(value, dict):
        for key in sorted(value):
            child = f"{field}.{key}"
            if PROHIBITED_KEY_RE.search(str(key)):
                findings.append(Finding("prohibited-field", child, "Ledger contains a prohibited private or credential-related field"))
            findings.extend(_privacy_findings(value[key], child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(_privacy_findings(item, f"{field}[{index}]"))
    elif isinstance(value, str) and SECRET_RE.search(value):
        findings.append(Finding("apparent-secret", field, "Ledger contains text resembling a credential or private key"))
    return findings


def validate_ledger(ledger: Any, receipt_files: dict[str, Path] | None = None) -> list[Finding]:
    findings: list[Finding] = []
    if not isinstance(ledger, dict):
        return [Finding("invalid-json-shape", "ledger", "Ledger root must be a JSON object")]

    findings.extend(_privacy_findings(ledger))
    expected_top = {"schema", "schema_version", "validator_version", "entries"}
    for field in sorted(expected_top - set(ledger)):
        findings.append(Finding("missing-field", field, f"Required ledger field is missing: {field}"))
    for field in sorted(set(ledger) - expected_top):
        findings.append(Finding("unsupported-field", field, f"Unsupported ledger field: {field}"))

    if ledger.get("schema") != SCHEMA:
        findings.append(Finding("unsupported-schema", "schema", f"Schema must be {SCHEMA}"))
    if ledger.get("schema_version") != VERSION:
        findings.append(Finding("unsupported-version", "schema_version", f"Schema version must be {VERSION}"))
    if ledger.get("validator_version") != TOOL_VERSION:
        findings.append(Finding("unsupported-validator", "validator_version", f"Validator version must be {TOOL_VERSION}"))

    entries = ledger.get("entries")
    if not isinstance(entries, list) or not entries:
        findings.append(Finding("invalid-entries", "entries", "entries must be a non-empty array"))
        return sorted(set(findings))

    expected_entry = {
        "sequence",
        "recorded_at",
        "receipt_sha256",
        "predecessor_receipt_sha256",
        "release_identity",
        "status",
        "reason",
        "owner",
    }
    seen_sequences: dict[int, int] = {}
    seen_digests: dict[str, int] = {}
    seen_identities: dict[str, int] = {}
    parsed_times: list[datetime | None] = []
    current_indices: list[int] = []

    for index, entry in enumerate(entries):
        prefix = f"entries[{index}]"
        if not isinstance(entry, dict):
            findings.append(Finding("invalid-entry", prefix, "Ledger entry must be an object"))
            parsed_times.append(None)
            continue
        for field in sorted(expected_entry - set(entry)):
            findings.append(Finding("missing-field", f"{prefix}.{field}", f"Required entry field is missing: {field}"))
        for field in sorted(set(entry) - expected_entry):
            findings.append(Finding("unsupported-field", f"{prefix}.{field}", f"Unsupported entry field: {field}"))

        sequence = entry.get("sequence")
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
            findings.append(Finding("invalid-sequence", f"{prefix}.sequence", "sequence must be a positive integer"))
        else:
            if sequence in seen_sequences:
                findings.append(Finding("duplicate-sequence", f"{prefix}.sequence", f"sequence duplicates entries[{seen_sequences[sequence]}]"))
            seen_sequences[sequence] = index
            if sequence != index + 1:
                findings.append(Finding("sequence-gap", f"{prefix}.sequence", f"sequence must equal {index + 1}"))

        recorded_at = entry.get("recorded_at")
        parsed = _parse_utc(recorded_at) if isinstance(recorded_at, str) else None
        parsed_times.append(parsed)
        if parsed is None:
            findings.append(Finding("invalid-timestamp", f"{prefix}.recorded_at", "recorded_at must be an ISO-8601 UTC timestamp"))
        elif index and parsed_times[index - 1] is not None and parsed <= parsed_times[index - 1]:
            findings.append(Finding("timestamp-regression", f"{prefix}.recorded_at", "recorded_at must be strictly later than the prior entry"))

        digest = entry.get("receipt_sha256")
        if not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest):
            findings.append(Finding("invalid-digest", f"{prefix}.receipt_sha256", "receipt_sha256 must be 64 lowercase hexadecimal characters"))
        else:
            if digest in seen_digests:
                findings.append(Finding("replayed-receipt", f"{prefix}.receipt_sha256", f"receipt digest duplicates entries[{seen_digests[digest]}]"))
            seen_digests[digest] = index

        predecessor = entry.get("predecessor_receipt_sha256")
        if index == 0:
            if predecessor is not None:
                findings.append(Finding("invalid-predecessor", f"{prefix}.predecessor_receipt_sha256", "first entry must have no predecessor"))
        else:
            expected_predecessor = entries[index - 1].get("receipt_sha256") if isinstance(entries[index - 1], dict) else None
            if not isinstance(predecessor, str) or not DIGEST_RE.fullmatch(predecessor):
                findings.append(Finding("invalid-predecessor", f"{prefix}.predecessor_receipt_sha256", "later entries must reference one valid predecessor digest"))
            elif predecessor != expected_predecessor:
                code = "cycle" if predecessor == digest else "fork-or-gap"
                findings.append(Finding(code, f"{prefix}.predecessor_receipt_sha256", "predecessor must equal the immediately prior receipt digest"))

        identity = entry.get("release_identity")
        if not isinstance(identity, str) or not SHA_RE.fullmatch(identity):
            findings.append(Finding("invalid-release-identity", f"{prefix}.release_identity", "release_identity must be a 40-character lowercase commit SHA"))
        else:
            if identity in seen_identities:
                findings.append(Finding("duplicate-release-identity", f"{prefix}.release_identity", f"release identity duplicates entries[{seen_identities[identity]}]"))
            seen_identities[identity] = index

        status = entry.get("status")
        if status not in STATUSES:
            findings.append(Finding("invalid-status", f"{prefix}.status", "status must be current, superseded, or revoked"))
        elif status == "current":
            current_indices.append(index)
        if index < len(entries) - 1 and status == "current":
            findings.append(Finding("nonfinal-current", f"{prefix}.status", "only the final entry may be current"))
        if index == len(entries) - 1 and status != "current":
            findings.append(Finding("final-not-current", f"{prefix}.status", "final entry must be current"))

        reason = entry.get("reason")
        owner = entry.get("owner")
        if status in {"superseded", "revoked"}:
            if not isinstance(reason, str) or not reason.strip():
                findings.append(Finding("missing-reason", f"{prefix}.reason", "superseded or revoked entries require a nonblank reason"))
            if not isinstance(owner, str) or not owner.strip():
                findings.append(Finding("missing-owner", f"{prefix}.owner", "superseded or revoked entries require a nonblank owner"))
        else:
            if reason is not None and not isinstance(reason, str):
                findings.append(Finding("invalid-reason", f"{prefix}.reason", "reason must be a string or null"))
            if owner is not None and not isinstance(owner, str):
                findings.append(Finding("invalid-owner", f"{prefix}.owner", "owner must be a string or null"))

    if len(current_indices) != 1:
        findings.append(Finding("current-count", "entries", "ledger must contain exactly one current entry"))
    elif current_indices[0] != len(entries) - 1:
        findings.append(Finding("current-not-final", f"entries[{current_indices[0]}].status", "current entry must be the final sequence entry"))

    if receipt_files:
        receipt_validator = _load_receipt_validator()
        for digest, path in sorted(receipt_files.items()):
            field = f"receipts.{digest}"
            if not DIGEST_RE.fullmatch(digest):
                findings.append(Finding("invalid-receipt-map-digest", field, "receipt mapping digest must be 64 lowercase hexadecimal characters"))
                continue
            if digest not in seen_digests:
                findings.append(Finding("unreferenced-receipt", field, "supplied receipt is not referenced by the ledger"))
                continue
            try:
                raw = path.read_bytes()
                receipt = json.loads(raw.decode("utf-8"))
            except OSError as exc:
                findings.append(Finding("receipt-unreadable", field, str(exc)))
                continue
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                findings.append(Finding("receipt-malformed", field, str(exc)))
                continue
            actual = _sha256_bytes(raw)
            if actual != digest:
                findings.append(Finding("receipt-digest-mismatch", field, "supplied receipt bytes do not match the ledger digest"))
            if not isinstance(receipt, dict) or receipt.get("schema") != receipt_validator.SCHEMA:
                findings.append(Finding("receipt-schema-invalid", field, "supplied receipt does not use the launch evidence-chain receipt schema"))

    return sorted(set(findings))


def _receipt_mapping(values: list[str]) -> tuple[dict[str, Path], list[str]]:
    result: dict[str, Path] = {}
    errors: list[str] = []
    for value in values:
        digest, separator, path = value.partition("=")
        if not separator or not digest or not path:
            errors.append(value)
            continue
        result[digest] = Path(path)
    return result, errors


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--receipt", action="append", default=[], metavar="DIGEST=PATH")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
    except OSError as exc:
        print(f"ERROR ledger-unreadable [ledger]: {exc}")
        return 1
    except json.JSONDecodeError as exc:
        print(f"ERROR malformed-json [ledger]: {exc}")
        return 1

    mappings, mapping_errors = _receipt_mapping(args.receipt)
    if mapping_errors:
        for value in sorted(mapping_errors):
            print(f"ERROR invalid-receipt-mapping [--receipt]: {value}")
        print(f"INVALID: {len(mapping_errors)} finding(s)")
        return 1

    findings = validate_ledger(ledger, mappings)
    if findings:
        for finding in findings:
            print(f"ERROR {finding.code} [{finding.field}]: {finding.message}")
        print(f"INVALID: {len(findings)} finding(s)")
        return 1
    print("VALID: launch receipt ledger ordering and integrity relationships are consistent")
    print("NOTICE: this result does not authorize staging, production, registration, payment, beta, or general availability")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
