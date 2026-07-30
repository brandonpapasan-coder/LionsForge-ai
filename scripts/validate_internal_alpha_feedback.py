#!/usr/bin/env python3
"""Validate privacy-safe, fail-closed internal-alpha feedback manifests."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SHA40 = re.compile(r"^[0-9a-f]{40}$")
IDENT = re.compile(r"^[a-z0-9][a-z0-9_-]{7,63}$")
RC = re.compile(r"^rc_[a-z0-9][a-z0-9._-]{5,63}$")
CODE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")
TOP = {"schema", "schema_version", "candidate_sha", "authorization", "environment", "feedback"}
ITEM = {"feedback_id", "tester_id", "session_id", "release_candidate", "category", "severity", "reproducibility", "component_code", "reason_codes", "observed_at", "session_starts_at", "session_ends_at"}
CATEGORIES = {"defect", "usability", "research-quality", "performance", "accessibility"}
SEVERITIES = {"low", "medium", "high", "critical"}
REPRO = {"always", "intermittent", "once", "not-applicable"}
FORBIDDEN = ("email", "name", "phone", "address", "password", "secret", "token", "api_key", "credential", "description", "comment", "message", "text", "attachment")


def canonical_digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def parse_time(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{field} must be RFC3339 UTC")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{field} must be RFC3339 UTC") from exc


def reject_sensitive_keys(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if any(marker in str(key).lower() for marker in FORBIDDEN):
                raise ValueError("personal, secret-like, or free-form key is forbidden")
            reject_sensitive_keys(item)
    elif isinstance(value, list):
        for item in value:
            reject_sensitive_keys(item)


def validate(value: object, expected_candidate: str | None = None, *, now: datetime | None = None) -> dict[str, object]:
    now = now or datetime.now(timezone.utc)
    if not isinstance(value, dict) or set(value) != TOP:
        raise ValueError("invalid manifest keys")
    reject_sensitive_keys(value)
    if value["schema"] != "lionsforge.internal-alpha.feedback" or value["schema_version"] != 1:
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
    feedback = value["feedback"]
    if not isinstance(feedback, list) or not feedback or len(feedback) > 500:
        raise ValueError("feedback must contain 1 to 500 entries")

    seen: set[str] = set()
    normalized: list[dict[str, object]] = []
    for item in feedback:
        if not isinstance(item, dict) or set(item) != ITEM:
            raise ValueError("invalid feedback keys")
        for field in ("feedback_id", "tester_id", "session_id"):
            field_value = item[field]
            if not isinstance(field_value, str) or not IDENT.fullmatch(field_value):
                raise ValueError(f"invalid {field}")
        if item["feedback_id"] in seen:
            raise ValueError("duplicate feedback_id")
        seen.add(item["feedback_id"])
        release = item["release_candidate"]
        if not isinstance(release, str) or not RC.fullmatch(release):
            raise ValueError("invalid release_candidate")
        if item["category"] not in CATEGORIES:
            raise ValueError("invalid feedback category")
        if item["severity"] not in SEVERITIES:
            raise ValueError("invalid feedback severity")
        if item["reproducibility"] not in REPRO:
            raise ValueError("invalid reproducibility")
        if item["category"] != "defect" and item["severity"] == "critical":
            raise ValueError("critical severity is reserved for defects")
        if item["category"] == "defect" and item["reproducibility"] == "not-applicable":
            raise ValueError("defects require reproducibility")
        component = item["component_code"]
        if not isinstance(component, str) or not CODE.fullmatch(component):
            raise ValueError("invalid component_code")
        reasons = item["reason_codes"]
        if not isinstance(reasons, list) or not reasons or len(reasons) > 10:
            raise ValueError("reason_codes must contain 1 to 10 entries")
        if any(not isinstance(code, str) or not CODE.fullmatch(code) for code in reasons) or len(set(reasons)) != len(reasons):
            raise ValueError("invalid or duplicate reason code")
        observed = parse_time(item["observed_at"], "observed_at")
        starts = parse_time(item["session_starts_at"], "session_starts_at")
        ends = parse_time(item["session_ends_at"], "session_ends_at")
        if observed > now + timedelta(minutes=5):
            raise ValueError("future observation")
        if ends <= starts:
            raise ValueError("invalid session window")
        if observed < starts or observed > ends:
            raise ValueError("observation outside session window")
        normalized.append(dict(item))

    normalized.sort(key=lambda item: str(item["feedback_id"]))
    counts = {category: sum(1 for item in normalized if item["category"] == category) for category in sorted(CATEGORIES)}
    report = {
        "schema": "lionsforge.internal-alpha.feedback-report",
        "schema_version": 1,
        "candidate_sha": candidate,
        "authorization": "INTERNAL-ALPHA-ONLY",
        "environment": "isolated-internal-alpha",
        "feedback_count": len(normalized),
        "feedback_ids": [item["feedback_id"] for item in normalized],
        "category_counts": counts,
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
