#!/usr/bin/env python3
"""Validate one replay-resistant public-operations freshness receipt."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
RECEIPT_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{7,127}$")
SAFE_PATH = re.compile(r"^[A-Za-z0-9._/-]+$")
ALLOWED = {
    "schema", "schema_version", "candidate_sha", "decision", "freshness_state",
    "freshness_report_path", "freshness_report_sha256", "freshness_digest",
    "receipt_id", "nonce_sha256", "issued_at",
}
FORBIDDEN = ("password", "secret", "token", "api_key", "private_key", "credential")


def parse_time(value: object, name: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{name} must be an RFC3339 UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be an RFC3339 UTC timestamp") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError(f"{name} must be UTC")
    return parsed


def safe_file(root: Path, relative: object) -> Path:
    if not isinstance(relative, str) or not SAFE_PATH.fullmatch(relative):
        raise ValueError("unsafe freshness report path")
    if relative.startswith("/") or ".." in Path(relative).parts:
        raise ValueError("unsafe freshness report path")
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise ValueError("freshness report missing or symlinked")
    return path


def canonical_digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def validate(
    receipt: dict[str, object],
    root: Path,
    expected_candidate: str | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    unknown = set(receipt) - ALLOWED
    missing = ALLOWED - set(receipt)
    if unknown or missing:
        raise ValueError("invalid top-level keys")
    if any(term in str(key).lower() for key in receipt for term in FORBIDDEN):
        raise ValueError("secret-like key detected")
    if receipt["schema"] != "lionsforge.public-operations-freshness-receipt" or receipt["schema_version"] != 1:
        raise ValueError("unsupported schema")

    candidate = receipt["candidate_sha"]
    if not isinstance(candidate, str) or not SHA40.fullmatch(candidate):
        raise ValueError("invalid candidate SHA")
    if expected_candidate and candidate != expected_candidate:
        raise ValueError("expected candidate mismatch")
    if receipt["decision"] != "NO-GO" or receipt["freshness_state"] != "VALID-NO-GO":
        raise ValueError("receipt must remain VALID-NO-GO")

    source_digest = receipt["freshness_report_sha256"]
    freshness_digest = receipt["freshness_digest"]
    nonce_digest = receipt["nonce_sha256"]
    for name, value in (
        ("freshness report digest", source_digest),
        ("freshness digest", freshness_digest),
        ("nonce digest", nonce_digest),
    ):
        if not isinstance(value, str) or not SHA256.fullmatch(value) or value == "0" * 64:
            raise ValueError(f"invalid {name}")
    if len({source_digest, freshness_digest, nonce_digest}) != 3:
        raise ValueError("receipt identity digests must be distinct")

    receipt_id = receipt["receipt_id"]
    if not isinstance(receipt_id, str) or not RECEIPT_ID.fullmatch(receipt_id):
        raise ValueError("invalid receipt ID")

    path = safe_file(root, receipt["freshness_report_path"])
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != source_digest:
        raise ValueError("freshness report digest mismatch")
    try:
        source = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("freshness report is not valid JSON") from exc
    if not isinstance(source, dict):
        raise ValueError("freshness report must be an object")
    if source.get("candidate_sha") != candidate:
        raise ValueError("freshness report candidate drift")
    if source.get("decision") != "NO-GO" or source.get("freshness_state") != "VALID-NO-GO":
        raise ValueError("freshness report state drift")
    if source.get("freshness_digest") != freshness_digest:
        raise ValueError("freshness digest drift")

    issued_at = parse_time(receipt["issued_at"], "issued_at")
    current = now or datetime.now(timezone.utc)
    if issued_at > current:
        raise ValueError("receipt cannot be issued in the future")

    core = {
        "candidate_sha": candidate,
        "decision": "NO-GO",
        "freshness_state": "VALID-NO-GO",
        "freshness_report_sha256": source_digest,
        "freshness_digest": freshness_digest,
        "receipt_id": receipt_id,
        "nonce_sha256": nonce_digest,
        "issued_at": receipt["issued_at"],
    }
    result = {
        "schema": "lionsforge.public-operations-freshness-receipt-report",
        "schema_version": 1,
        **core,
        "receipt_state": "VALID-NO-GO",
    }
    result["receipt_digest"] = canonical_digest(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("receipt")
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--expected-candidate")
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
        if not isinstance(receipt, dict):
            raise ValueError("receipt must be a JSON object")
        result = validate(receipt, Path(args.repository_root), args.expected_candidate)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"BLOCKED: {exc}")
        return 1
    rendered = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
