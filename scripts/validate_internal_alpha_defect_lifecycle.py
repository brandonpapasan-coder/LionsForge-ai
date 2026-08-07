#!/usr/bin/env python3
"""Validate privacy-safe, fail-closed internal-alpha defect lifecycle manifests."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SHA40 = re.compile(r"^[0-9a-f]{40}$")
IDENT = re.compile(r"^[a-z0-9][a-z0-9_-]{7,63}$")
RC = re.compile(r"^rc_[a-z0-9][a-z0-9._-]{5,63}$")
CODE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")
TOP = {"schema", "schema_version", "candidate_sha", "authorization", "environment", "defects"}
ITEM = {
    "defect_id", "feedback_id", "tester_id", "session_id", "release_candidate",
    "severity", "previous_severity", "state", "previous_state", "regression",
    "owner_ref", "reason_codes", "created_at", "updated_at", "verified_at",
}
SEVERITIES = {"low": 0, "medium": 1, "high": 2, "critical": 3}
STATES = {"triaged": 0, "accepted": 1, "in-progress": 2, "fixed": 3, "verified": 4, "closed": 5, "rejected": 5}
REGRESSION = {"none", "suspected", "confirmed"}
FORBIDDEN = (
    "email", "name", "phone", "address", "password", "secret", "token", "api_key",
    "credential", "description", "comment", "message", "text", "attachment",
)


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def parse_time(value: object, field: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{field} must be RFC3339 UTC or null")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{field} must be RFC3339 UTC or null") from exc


def reject_sensitive_keys(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if any(marker in str(key).lower() for marker in FORBIDDEN):
                raise ValueError("personal, secret-like, or free-form key is forbidden")
            reject_sensitive_keys(item)
    elif isinstance(value, list):
        for item in value:
            reject_sensitive_keys(item)


def validate(
    value: object,
    expected_candidate: str | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    now = now or datetime.now(timezone.utc)
    if not isinstance(value, dict) or set(value) != TOP:
        raise ValueError("invalid manifest keys")
    reject_sensitive_keys(value)
    if value["schema"] != "lionsforge.internal-alpha.defect-lifecycle" or value["schema_version"] != 1:
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
    defects = value["defects"]
    if not isinstance(defects, list) or not defects or len(defects) > 500:
        raise ValueError("defects must contain 1 to 500 entries")

    ids: set[str] = set()
    feedback_ids: set[str] = set()
    normalized: list[dict[str, object]] = []
    for item in defects:
        if not isinstance(item, dict) or set(item) != ITEM:
            raise ValueError("invalid defect keys")
        for field in ("defect_id", "feedback_id", "tester_id", "session_id", "owner_ref"):
            if not isinstance(item[field], str) or not IDENT.fullmatch(item[field]):
                raise ValueError(f"invalid {field}")
        if not isinstance(item["release_candidate"], str) or not RC.fullmatch(item["release_candidate"]):
            raise ValueError("invalid release_candidate")
        if item["defect_id"] in ids:
            raise ValueError("duplicate defect_id")
        ids.add(item["defect_id"])
        if item["feedback_id"] in feedback_ids:
            raise ValueError("duplicate feedback_id")
        feedback_ids.add(item["feedback_id"])

        severity = item["severity"]
        previous_severity = item["previous_severity"]
        state = item["state"]
        previous_state = item["previous_state"]
        if severity not in SEVERITIES or previous_severity not in SEVERITIES:
            raise ValueError("invalid severity")
        if state not in STATES or previous_state not in STATES:
            raise ValueError("invalid lifecycle state")
        if item["regression"] not in REGRESSION:
            raise ValueError("invalid regression state")

        reasons = item["reason_codes"]
        if (
            not isinstance(reasons, list)
            or not reasons
            or len(reasons) > 8
            or len(set(reasons)) != len(reasons)
        ):
            raise ValueError("reason_codes must contain 1 to 8 unique entries")
        if any(not isinstance(code, str) or not CODE.fullmatch(code) for code in reasons):
            raise ValueError("invalid reason code")
        if state != "rejected" and STATES[state] < STATES[previous_state]:
            raise ValueError("lifecycle transition regression")
        if (
            SEVERITIES[severity] < SEVERITIES[previous_severity]
            and "severity-downgrade-approved" not in reasons
        ):
            raise ValueError("severity downgrade requires approval reason")

        created = parse_time(item["created_at"], "created_at")
        updated = parse_time(item["updated_at"], "updated_at")
        verified = parse_time(item["verified_at"], "verified_at")
        assert created and updated
        if created > now or updated > now or (verified and verified > now):
            raise ValueError("future lifecycle timestamp")
        if updated < created or (verified and verified < created):
            raise ValueError("invalid lifecycle timestamp ordering")
        if state in {"verified", "closed"} and verified is None:
            raise ValueError("verified_at is required")
        if state not in {"verified", "closed"} and verified is not None:
            raise ValueError("verified_at is only valid for verified or closed defects")
        normalized.append(dict(item))

    normalized.sort(key=lambda row: str(row["defect_id"]))
    report: dict[str, object] = {
        "schema": "lionsforge.internal-alpha.defect-lifecycle-report",
        "schema_version": 1,
        "candidate_sha": candidate,
        "authorization": "INTERNAL-ALPHA-ONLY",
        "environment": "isolated-internal-alpha",
        "defect_count": len(normalized),
        "defect_ids": [row["defect_id"] for row in normalized],
        "open_count": sum(row["state"] not in {"closed", "rejected"} for row in normalized),
        "critical_count": sum(row["severity"] == "critical" for row in normalized),
        "confirmed_regression_count": sum(row["regression"] == "confirmed" for row in normalized),
        "manifest_digest": digest(value),
    }
    report["report_digest"] = digest(report)
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
        rendered = json.dumps(report, sort_keys=True, indent=2) + "\n"
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
