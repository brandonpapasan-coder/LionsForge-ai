#!/usr/bin/env python3
"""Generate or validate a LionsForge AI launch evidence-chain receipt.

The receipt binds four non-secret Markdown records to their SHA-256 digests and
release identity. It verifies file integrity and record-chain consistency only;
it does not verify live evidence or authorize launch.
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
CHAIN_VALIDATOR = ROOT / "scripts" / "validate_launch_evidence_chain.py"
SCHEMA = "lionsforge.launch-evidence-chain-receipt"
VERSION = 1
TOOL_VERSION = "1.0.0"
RECORD_KINDS = ("production", "public_operations", "controlled_beta", "ga")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
FILE_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
FIELD_RE = re.compile(r"^- ([^:]+):\s*(.*)$")
CHECKBOX_DECISION_RE = re.compile(r"^- \[([ xX])\]\s+(GO|CONDITIONAL GO|NO-GO)\b")


@dataclass(frozen=True, order=True)
class Finding:
    code: str
    field: str
    message: str


def _load_chain_validator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("launch_receipt_chain_validator", CHAIN_VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load chain validator: {CHAIN_VALIDATOR}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _normalize(value: str) -> str:
    return value.strip().strip("`").strip()


def _fields(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        match = FIELD_RE.match(line.strip())
        if match:
            result[match.group(1).strip()] = _normalize(match.group(2))
    return result


def _decision(text: str, fields: dict[str, str]) -> str:
    direct = fields.get("Decision", "").upper()
    if direct in {"GO", "CONDITIONAL GO", "NO-GO"}:
        return direct
    selected: list[str] = []
    for line in text.splitlines():
        match = CHECKBOX_DECISION_RE.match(line.strip())
        if match and match.group(1).lower() == "x":
            selected.append(match.group(2))
    return selected[0] if len(selected) == 1 else ""


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def _parse_utc(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        return None
    return parsed


def _identity(records: dict[str, str]) -> dict[str, str]:
    ga_fields = _fields(records["ga"])
    return {
        "release_sha": ga_fields.get("Release SHA", ""),
        "rollback_sha": ga_fields.get("Previous rollback SHA", ""),
        "backend_image_digest": ga_fields.get("Backend image digest", ""),
        "frontend_image_digest": ga_fields.get("Frontend image digest", ""),
        "ga_decision": _decision(records["ga"], ga_fields),
    }


def build_receipt(records: dict[str, str], generated_at: datetime | None = None) -> dict[str, Any]:
    chain = _load_chain_validator()
    findings = chain.validate_chain(records)
    if findings:
        details = "; ".join(
            f"{getattr(item, 'record', 'chain')}:{getattr(item, 'code', 'invalid')}"
            for item in findings
        )
        raise ValueError(f"launch evidence chain is invalid: {details}")

    timestamp = generated_at or datetime.now(timezone.utc)
    if timestamp.tzinfo is None or timestamp.utcoffset() != timezone.utc.utcoffset(timestamp):
        raise ValueError("generated_at must be timezone-aware UTC")
    timestamp = timestamp.astimezone(timezone.utc).replace(microsecond=0)

    return {
        "schema": SCHEMA,
        "schema_version": VERSION,
        "validator_version": TOOL_VERSION,
        "generated_at": timestamp.isoformat().replace("+00:00", "Z"),
        "result": "VALID",
        "identity": _identity(records),
        "records": {kind: {"sha256": _sha256_text(records[kind])} for kind in RECORD_KINDS},
    }


def validate_receipt(receipt: Any, records: dict[str, str]) -> list[Finding]:
    findings: list[Finding] = []
    if not isinstance(receipt, dict):
        return [Finding("invalid-json-shape", "receipt", "Receipt root must be a JSON object")]

    expected_top = {
        "schema",
        "schema_version",
        "validator_version",
        "generated_at",
        "result",
        "identity",
        "records",
    }
    missing = sorted(expected_top - set(receipt))
    extra = sorted(set(receipt) - expected_top)
    for field in missing:
        findings.append(Finding("missing-field", field, f"Required receipt field is missing: {field}"))
    for field in extra:
        findings.append(Finding("unsupported-field", field, f"Unsupported receipt field: {field}"))

    if receipt.get("schema") != SCHEMA:
        findings.append(Finding("unsupported-schema", "schema", f"Schema must be {SCHEMA}"))
    if receipt.get("schema_version") != VERSION:
        findings.append(Finding("unsupported-version", "schema_version", f"Schema version must be {VERSION}"))
    if receipt.get("validator_version") != TOOL_VERSION:
        findings.append(Finding("unsupported-validator", "validator_version", f"Validator version must be {TOOL_VERSION}"))
    if receipt.get("result") != "VALID":
        findings.append(Finding("invalid-result", "result", "Receipt result must be VALID"))

    generated_at = receipt.get("generated_at")
    if not isinstance(generated_at, str) or _parse_utc(generated_at) is None:
        findings.append(Finding("invalid-timestamp", "generated_at", "generated_at must be an ISO-8601 UTC timestamp"))

    chain = _load_chain_validator()
    for item in chain.validate_chain(records):
        findings.append(
            Finding(
                "chain-invalid",
                getattr(item, "record", "chain"),
                f"{getattr(item, 'code', 'invalid')}: {getattr(item, 'message', item)}",
            )
        )

    record_bindings = receipt.get("records")
    if not isinstance(record_bindings, dict):
        findings.append(Finding("invalid-records", "records", "records must be an object"))
        record_bindings = {}
    else:
        for extra_kind in sorted(set(record_bindings) - set(RECORD_KINDS)):
            findings.append(Finding("unsupported-record", f"records.{extra_kind}", f"Unsupported record binding: {extra_kind}"))

    seen_digests: dict[str, str] = {}
    for kind in RECORD_KINDS:
        binding = record_bindings.get(kind)
        if not isinstance(binding, dict) or set(binding) != {"sha256"}:
            findings.append(Finding("invalid-binding", f"records.{kind}", f"{kind} binding must contain only sha256"))
            continue
        digest = binding.get("sha256")
        if not isinstance(digest, str) or not FILE_DIGEST_RE.fullmatch(digest):
            findings.append(Finding("invalid-digest", f"records.{kind}.sha256", f"{kind} sha256 must be 64 lowercase hexadecimal characters"))
            continue
        expected = _sha256_text(records[kind])
        if digest != expected:
            findings.append(Finding("record-drift", f"records.{kind}.sha256", f"{kind} record content does not match the receipt"))
        previous = seen_digests.get(digest)
        if previous is not None and records[previous] != records[kind]:
            findings.append(Finding("duplicate-binding", f"records.{kind}.sha256", f"{kind} shares a digest with {previous} despite differing content"))
        seen_digests[digest] = kind

    identity = receipt.get("identity")
    expected_identity = _identity(records)
    identity_fields = {
        "release_sha": SHA_RE,
        "rollback_sha": SHA_RE,
        "backend_image_digest": DIGEST_RE,
        "frontend_image_digest": DIGEST_RE,
        "ga_decision": None,
    }
    if not isinstance(identity, dict):
        findings.append(Finding("invalid-identity", "identity", "identity must be an object"))
        identity = {}
    elif set(identity) != set(identity_fields):
        findings.append(Finding("invalid-identity", "identity", "identity fields do not match the receipt schema"))

    for field, pattern in identity_fields.items():
        value = identity.get(field)
        if not isinstance(value, str):
            findings.append(Finding("invalid-identity-value", f"identity.{field}", f"Identity field must be a string: {field}"))
            continue
        if pattern is not None and not pattern.fullmatch(value):
            findings.append(Finding("invalid-identity-value", f"identity.{field}", f"Identity field has invalid format: {field}"))
        if field == "ga_decision" and value not in {"GO", "NO-GO"}:
            findings.append(Finding("invalid-identity-value", f"identity.{field}", "GA decision must be GO or NO-GO"))
        if value != expected_identity.get(field):
            findings.append(Finding("identity-drift", f"identity.{field}", f"Receipt identity does not match current records: {field}"))

    return sorted(findings)


def _read_records(paths: list[Path]) -> dict[str, str]:
    records: dict[str, str] = {}
    for kind, path in zip(RECORD_KINDS, paths, strict=True):
        try:
            records[kind] = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise OSError(f"record-unreadable [{kind}]: {exc}") from exc
    return records


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("generate", "validate"):
        sub = subparsers.add_parser(command)
        sub.add_argument("production", type=Path)
        sub.add_argument("public_operations", type=Path)
        sub.add_argument("controlled_beta", type=Path)
        sub.add_argument("ga", type=Path)
        if command == "generate":
            sub.add_argument("--output", type=Path)
        else:
            sub.add_argument("receipt", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    paths = [args.production, args.public_operations, args.controlled_beta, args.ga]
    try:
        records = _read_records(paths)
    except OSError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1

    if args.command == "generate":
        try:
            receipt = build_receipt(records)
        except (RuntimeError, ValueError) as exc:
            print(f"ERROR receipt-not-generated: {exc}", file=sys.stderr)
            return 1
        content = _canonical_json(receipt)
        if args.output:
            try:
                args.output.write_text(content, encoding="utf-8")
            except OSError as exc:
                print(f"ERROR receipt-unwritable: {exc}", file=sys.stderr)
                return 1
        else:
            sys.stdout.write(content)
        return 0

    try:
        receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    except OSError as exc:
        print(f"ERROR receipt-unreadable: {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"ERROR malformed-json: {exc}")
        return 1

    findings = validate_receipt(receipt, records)
    if findings:
        for finding in findings:
            print(f"ERROR {finding.code} [{finding.field}]: {finding.message}")
        print(f"INVALID: {len(findings)} finding(s)")
        return 1
    print("VALID: launch evidence-chain receipt matches all supplied records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
