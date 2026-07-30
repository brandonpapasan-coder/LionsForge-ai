#!/usr/bin/env python3
"""Validate fail-closed internal-alpha session assignments."""
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
TOP = {"schema", "schema_version", "candidate_sha", "authorization", "environment", "sessions"}
SESSION = {"session_id", "tester_id", "release_candidate", "purpose", "approver_ref", "issued_at", "starts_at", "ends_at"}
PURPOSES = {"research", "validation", "usability"}
FORBIDDEN = ("email", "name", "phone", "address", "password", "secret", "token", "api_key", "credential")


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
                raise ValueError("personal or secret-like key is forbidden")
            reject_sensitive_keys(item)
    elif isinstance(value, list):
        for item in value:
            reject_sensitive_keys(item)


def validate(value: object, expected_candidate: str | None = None, *, now: datetime | None = None) -> dict[str, object]:
    now = now or datetime.now(timezone.utc)
    if not isinstance(value, dict) or set(value) != TOP:
        raise ValueError("invalid manifest keys")
    reject_sensitive_keys(value)
    if value["schema"] != "lionsforge.internal-alpha.session-assignment" or value["schema_version"] != 1:
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
    sessions = value["sessions"]
    if not isinstance(sessions, list) or not sessions or len(sessions) > 200:
        raise ValueError("sessions must contain 1 to 200 entries")

    ids: set[str] = set()
    assignments: set[tuple[str, str]] = set()
    tester_windows: dict[str, list[tuple[datetime, datetime]]] = {}
    normalized: list[dict[str, object]] = []
    for session in sessions:
        if not isinstance(session, dict) or set(session) != SESSION:
            raise ValueError("invalid session keys")
        session_id = session["session_id"]
        tester_id = session["tester_id"]
        approver = session["approver_ref"]
        release = session["release_candidate"]
        if not isinstance(session_id, str) or not IDENT.fullmatch(session_id):
            raise ValueError("invalid session_id")
        if session_id in ids:
            raise ValueError("duplicate session_id")
        ids.add(session_id)
        if not isinstance(tester_id, str) or not IDENT.fullmatch(tester_id):
            raise ValueError("invalid tester_id")
        if not isinstance(approver, str) or not IDENT.fullmatch(approver):
            raise ValueError("invalid approver_ref")
        if not isinstance(release, str) or not RC.fullmatch(release):
            raise ValueError("invalid release_candidate")
        assignment = (tester_id, release)
        if assignment in assignments:
            raise ValueError("duplicate tester release assignment")
        assignments.add(assignment)
        if session["purpose"] not in PURPOSES:
            raise ValueError("purpose exceeds least privilege")
        issued = parse_time(session["issued_at"], "issued_at")
        starts = parse_time(session["starts_at"], "starts_at")
        ends = parse_time(session["ends_at"], "ends_at")
        if issued > now + timedelta(minutes=5):
            raise ValueError("future issuance")
        if starts < issued:
            raise ValueError("session starts before issuance")
        if ends <= now:
            raise ValueError("expired session")
        if ends <= starts or ends - starts > timedelta(hours=12):
            raise ValueError("session duration must be positive and at most 12 hours")
        for existing_start, existing_end in tester_windows.setdefault(tester_id, []):
            if starts < existing_end and existing_start < ends:
                raise ValueError("overlapping tester sessions")
        tester_windows[tester_id].append((starts, ends))
        normalized.append(dict(session))

    normalized.sort(key=lambda item: str(item["session_id"]))
    report = {
        "schema": "lionsforge.internal-alpha.session-assignment-report",
        "schema_version": 1,
        "candidate_sha": candidate,
        "authorization": "INTERNAL-ALPHA-ONLY",
        "environment": "isolated-internal-alpha",
        "session_count": len(normalized),
        "session_ids": [item["session_id"] for item in normalized],
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
