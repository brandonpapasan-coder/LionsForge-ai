#!/usr/bin/env python3
"""Generate and validate tamper-evident public-operations activation receipts."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "lionsforge.public-operations-activation-receipt"
SCHEMA_VERSION = 1
GENERATOR_VERSION = "1.0.0"
NOTICE = (
    "This receipt proves source-record integrity and candidate binding only. It does not perform legal review, "
    "test live operational channels, or authorize public registration, controlled beta, payments, or launch."
)
_SHA = re.compile(r"[0-9a-f]{40}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_SENSITIVE = re.compile(
    r"(?:password|api[_ -]?key|access[_ -]?token|refresh[_ -]?token|private[_ -]?key|client[_ -]?secret|credential)",
    re.IGNORECASE,
)


def _load_activation_validator():
    path = Path(__file__).with_name("validate_public_operations_activation.py")
    spec = importlib.util.spec_from_file_location("validate_public_operations_activation", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("public operations activation validator could not be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def canonical_record(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.rstrip() + "\n"


def canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def utc_z(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("timestamp must end in Z")
    return datetime.fromisoformat(value.removesuffix("Z") + "+00:00").astimezone(timezone.utc)


def validate_source_record(text: str) -> list[str]:
    canonical = canonical_record(text)
    findings: list[str] = []
    if _SENSITIVE.search(canonical):
        findings.append("activation record contains a prohibited sensitive-field term")
    validator = _load_activation_validator()
    findings.extend(f"activation-record:{item.code}:{item.message}" for item in validator.validate_record(canonical))
    return sorted(set(findings))


def _record_decision(text: str) -> str | None:
    for line in canonical_record(text).splitlines():
        if line.strip().startswith("- Decision:"):
            return line.split(":", 1)[1].strip().strip("`*").upper()
    return None


def build_receipt(*, record_text: str, candidate_sha: str, generated_at: datetime) -> dict[str, Any]:
    if not _SHA.fullmatch(candidate_sha):
        raise ValueError("candidate_sha must be a lowercase 40-character commit SHA")
    findings = validate_source_record(record_text)
    if findings:
        raise ValueError("activation record is not receipt-ready: " + "; ".join(findings))
    canonical = canonical_record(record_text)
    decision = _record_decision(canonical)
    if decision != "GO":
        raise ValueError("activation record decision must be GO")
    return {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "candidate_sha": candidate_sha,
        "decision": decision,
        "record_sha256": sha256_text(canonical),
        "record_bytes": len(canonical.encode("utf-8")),
        "generated_at": utc_z(generated_at),
        "interpretation_notice": NOTICE,
    }


def validate_receipt(
    value: Any,
    *,
    record_text: str | None = None,
    expected_candidate_sha: str | None = None,
) -> list[str]:
    if not isinstance(value, dict):
        return ["receipt must be an object"]
    required = {
        "schema",
        "schema_version",
        "generator_version",
        "candidate_sha",
        "decision",
        "record_sha256",
        "record_bytes",
        "generated_at",
        "interpretation_notice",
    }
    findings = [f"unexpected receipt field: {key}" for key in sorted(set(value) - required)]
    findings.extend(f"missing receipt field: {key}" for key in sorted(required - set(value)))
    if value.get("schema") != SCHEMA or value.get("schema_version") != SCHEMA_VERSION:
        findings.append("unsupported receipt schema or version")
    if value.get("generator_version") != GENERATOR_VERSION:
        findings.append("unsupported generator version")
    candidate_sha = value.get("candidate_sha")
    if not isinstance(candidate_sha, str) or not _SHA.fullmatch(candidate_sha):
        findings.append("candidate_sha must be a lowercase 40-character commit SHA")
    elif expected_candidate_sha is not None and candidate_sha != expected_candidate_sha:
        findings.append("candidate SHA mismatch")
    if value.get("decision") != "GO":
        findings.append("receipt decision must be GO")
    digest = value.get("record_sha256")
    if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
        findings.append("record_sha256 must be 64 lowercase hexadecimal characters")
    size = value.get("record_bytes")
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        findings.append("record_bytes must be a positive integer")
    try:
        parse_utc(value.get("generated_at"))
    except (TypeError, ValueError):
        findings.append("generated_at must be a valid UTC timestamp ending in Z")
    if value.get("interpretation_notice") != NOTICE:
        findings.append("interpretation notice mismatch")
    if record_text is not None:
        source_findings = validate_source_record(record_text)
        findings.extend(source_findings)
        canonical = canonical_record(record_text)
        if value.get("record_sha256") != sha256_text(canonical):
            findings.append("source record digest mismatch")
        if value.get("record_bytes") != len(canonical.encode("utf-8")):
            findings.append("source record byte length mismatch")
        if value.get("decision") != _record_decision(canonical):
            findings.append("source record decision mismatch")
    return sorted(set(findings))


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate")
    generate.add_argument("record", type=Path)
    generate.add_argument("--candidate-sha", required=True)
    generate.add_argument("--generated-at", required=True)
    generate.add_argument("--output", type=Path, required=True)

    validate = subparsers.add_parser("validate")
    validate.add_argument("receipt", type=Path)
    validate.add_argument("--record", type=Path)
    validate.add_argument("--expected-candidate-sha")

    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            receipt = build_receipt(
                record_text=args.record.read_text(encoding="utf-8"),
                candidate_sha=args.candidate_sha,
                generated_at=parse_utc(args.generated_at),
            )
            args.output.write_text(canonical_json(receipt), encoding="utf-8")
            print(canonical_json({"valid": True, "receipt_sha256": sha256_text(canonical_json(receipt))}), end="")
            return 0

        receipt = _read_json(args.receipt)
        record_text = args.record.read_text(encoding="utf-8") if args.record else None
        findings = validate_receipt(
            receipt,
            record_text=record_text,
            expected_candidate_sha=args.expected_candidate_sha,
        )
        print(canonical_json({"valid": not findings, "findings": findings}), end="")
        return 0 if not findings else 1
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(canonical_json({"valid": False, "findings": [str(exc)]}), end="")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
