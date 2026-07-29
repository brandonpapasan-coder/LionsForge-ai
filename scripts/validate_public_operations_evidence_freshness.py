#!/usr/bin/env python3
"""Validate freshness metadata for one reconciled public-operations evidence chain."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SAFE_PATH = re.compile(r"^[A-Za-z0-9._/-]+$")
ALLOWED = {
    "schema", "schema_version", "candidate_sha", "decision",
    "reconciliation_path", "reconciliation_sha256", "generated_at",
    "valid_until", "maximum_validity_hours", "owner_role", "reviewer_role",
}
FORBIDDEN = ("password", "secret", "token", "api_key", "private_key", "credential")


def parse_time(value: object, name: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{name} must be an RFC3339 UTC timestamp")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be an RFC3339 UTC timestamp") from exc


def safe_file(root: Path, relative: object) -> Path:
    if not isinstance(relative, str) or not SAFE_PATH.fullmatch(relative):
        raise ValueError("unsafe reconciliation path")
    if relative.startswith("/") or ".." in Path(relative).parts:
        raise ValueError("unsafe reconciliation path")
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise ValueError("reconciliation file missing or symlinked")
    return path


def canonical_digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def validate(record: dict[str, object], root: Path, expected_candidate: str | None = None,
             now: datetime | None = None) -> dict[str, object]:
    unknown = set(record) - ALLOWED
    missing = ALLOWED - set(record)
    if unknown or missing:
        raise ValueError("invalid top-level keys")
    if any(term in str(key).lower() for key in record for term in FORBIDDEN):
        raise ValueError("secret-like key detected")
    if record["schema"] != "lionsforge.public-operations-evidence-freshness" or record["schema_version"] != 1:
        raise ValueError("unsupported schema")
    candidate = record["candidate_sha"]
    if not isinstance(candidate, str) or not SHA40.fullmatch(candidate):
        raise ValueError("invalid candidate SHA")
    if expected_candidate and candidate != expected_candidate:
        raise ValueError("expected candidate mismatch")
    if record["decision"] != "NO-GO":
        raise ValueError("freshness record must remain NO-GO")
    digest = record["reconciliation_sha256"]
    if not isinstance(digest, str) or not SHA256.fullmatch(digest):
        raise ValueError("invalid reconciliation digest")
    path = safe_file(root, record["reconciliation_path"])
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError("reconciliation digest mismatch")
    source = json.loads(path.read_text(encoding="utf-8"))
    if source.get("candidate_sha") != candidate or source.get("decision") != "NO-GO":
        raise ValueError("reconciliation candidate or decision drift")
    generated = parse_time(record["generated_at"], "generated_at")
    valid_until = parse_time(record["valid_until"], "valid_until")
    hours = record["maximum_validity_hours"]
    if not isinstance(hours, int) or isinstance(hours, bool) or not 1 <= hours <= 720:
        raise ValueError("maximum_validity_hours must be 1..720")
    if valid_until <= generated:
        raise ValueError("valid_until must follow generated_at")
    if (valid_until - generated).total_seconds() > hours * 3600:
        raise ValueError("validity window exceeds maximum")
    current = now or datetime.now(timezone.utc)
    if current > valid_until:
        raise ValueError("freshness record expired")
    owner = record["owner_role"]
    reviewer = record["reviewer_role"]
    if not isinstance(owner, str) or not owner.strip() or not isinstance(reviewer, str) or not reviewer.strip():
        raise ValueError("owner and reviewer roles are required")
    if owner.strip().casefold() == reviewer.strip().casefold():
        raise ValueError("owner and reviewer roles must be separated")
    result = {
        "schema": "lionsforge.public-operations-evidence-freshness-report",
        "schema_version": 1,
        "candidate_sha": candidate,
        "decision": "NO-GO",
        "freshness_state": "VALID-NO-GO",
        "generated_at": record["generated_at"],
        "valid_until": record["valid_until"],
        "reconciliation_sha256": digest,
    }
    result["freshness_digest"] = canonical_digest(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("record")
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--expected-candidate")
    parser.add_argument("--output")
    args = parser.parse_args()
    record = json.loads(Path(args.record).read_text(encoding="utf-8"))
    result = validate(record, Path(args.repository_root).resolve(), args.expected_candidate)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
