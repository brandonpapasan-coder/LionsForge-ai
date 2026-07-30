#!/usr/bin/env python3
"""Validate a privacy-safe, fail-closed internal-alpha tester access manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SHA40 = re.compile(r"^[0-9a-f]{40}$")
ID = re.compile(r"^[a-z0-9][a-z0-9_-]{7,63}$")
TOP = {"schema", "schema_version", "candidate_sha", "authorization", "environment", "testers"}
TESTER = {"tester_id", "status", "role", "approver_ref", "issued_at", "expires_at"}
FORBIDDEN = ("email", "name", "phone", "address", "password", "secret", "token", "api_key", "credential")
ALLOWED_ROLES = {"reader", "researcher", "validator"}


def canonical_digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def parse_time(value: object, name: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{name} must be RFC3339 UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be RFC3339 UTC") from exc
    return parsed


def reject_secret_keys(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).lower()
            if any(marker in lowered for marker in FORBIDDEN):
                raise ValueError("personal or secret-like key is forbidden")
            reject_secret_keys(item)
    elif isinstance(value, list):
        for item in value:
            reject_secret_keys(item)


def validate(value: object, expected_candidate: str | None = None, *, now: datetime | None = None) -> dict[str, object]:
    now = now or datetime.now(timezone.utc)
    if not isinstance(value, dict) or set(value) != TOP:
        raise ValueError("invalid manifest keys")
    reject_secret_keys(value)
    if value["schema"] != "lionsforge.internal-alpha.tester-access" or value["schema_version"] != 1:
        raise ValueError("unsupported schema")
    candidate = value["candidate_sha"]
    if not isinstance(candidate, str) or not SHA40.fullmatch(candidate):
        raise ValueError("invalid candidate SHA")
    if expected_candidate and candidate != expected_candidate:
        raise ValueError("candidate mismatch")
    if value["authorization"] != "INTERNAL-ALPHA-ONLY":
        raise ValueError("authorization must be INTERNAL-ALPHA-ONLY")
    if value["environment"] != "isolated-internal-alpha":
        raise ValueError("environment must be isolated-internal-alpha")
    testers = value["testers"]
    if not isinstance(testers, list) or not testers or len(testers) > 100:
        raise ValueError("testers must contain 1 to 100 entries")

    seen: set[str] = set()
    normalized: list[dict[str, object]] = []
    for tester in testers:
        if not isinstance(tester, dict) or set(tester) != TESTER:
            raise ValueError("invalid tester keys")
        tester_id = tester["tester_id"]
        approver = tester["approver_ref"]
        if not isinstance(tester_id, str) or not ID.fullmatch(tester_id):
            raise ValueError("invalid tester_id")
        if tester_id in seen:
            raise ValueError("duplicate tester_id")
        seen.add(tester_id)
        if tester["status"] != "approved":
            raise ValueError("tester status must be approved")
        if tester["role"] not in ALLOWED_ROLES:
            raise ValueError("role exceeds internal-alpha least privilege")
        if not isinstance(approver, str) or not ID.fullmatch(approver):
            raise ValueError("invalid approver_ref")
        issued = parse_time(tester["issued_at"], "issued_at")
        expires = parse_time(tester["expires_at"], "expires_at")
        if issued > now + timedelta(minutes=5):
            raise ValueError("future issuance")
        if expires <= now:
            raise ValueError("expired access")
        if expires <= issued or expires - issued > timedelta(days=30):
            raise ValueError("access duration must be positive and at most 30 days")
        normalized.append(dict(tester))

    normalized.sort(key=lambda item: str(item["tester_id"]))
    report = {
        "schema": "lionsforge.internal-alpha.tester-access-report",
        "schema_version": 1,
        "candidate_sha": candidate,
        "authorization": "INTERNAL-ALPHA-ONLY",
        "environment": "isolated-internal-alpha",
        "tester_count": len(normalized),
        "tester_ids": [item["tester_id"] for item in normalized],
        "manifest_digest": canonical_digest(value),
    }
    report["report_digest"] = canonical_digest(report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--expected-candidate")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        value = json.loads(args.manifest.read_text(encoding="utf-8"))
        report = validate(value, args.expected_candidate)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    encoded = json.dumps(report, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
