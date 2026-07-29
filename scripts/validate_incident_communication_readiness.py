#!/usr/bin/env python3
"""Validate a versioned incident communication readiness record."""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REQUIRED = {"availability", "security", "privacy", "data-integrity", "provider-dependency"}
TOP = {"schema", "schema_version", "candidate_sha", "decision", "owner_role", "incident_classes"}
KEYS = {"id", "incident_commander_role", "backup_commander_role", "severity_threshold", "initial_update_target_minutes", "recurring_update_minutes", "user_notice_criteria", "restoration_message_process", "post_incident_review_target_days", "evidence_reference", "status"}
PLACEHOLDERS = {"", "TBD", "TODO", "PENDING", "NOT VERIFIED", "UNKNOWN", "N/A"}
FORBIDDEN = ("password", "secret", "token", "api_key", "private_key", "credential")


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or value.strip().upper() in PLACEHOLDERS or len(value.strip()) < 3:
        raise ValueError(f"{label} is incomplete")
    return value.strip()


def _positive(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _scan(value: object) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if any(term in key.lower() for term in FORBIDDEN):
                raise ValueError(f"forbidden secret-like key: {key}")
            _scan(nested)
    elif isinstance(value, list):
        for item in value:
            _scan(item)


def validate_record(value: object, expected_candidate: str | None = None) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != TOP:
        raise ValueError("top-level keys do not match contract")
    _scan(value)
    if value["schema"] != "lionsforge.incident-communication-readiness" or value["schema_version"] != 1:
        raise ValueError("schema is invalid")
    candidate = value["candidate_sha"]
    if not isinstance(candidate, str) or not SHA_RE.fullmatch(candidate):
        raise ValueError("candidate_sha is invalid")
    if expected_candidate and candidate != expected_candidate:
        raise ValueError("candidate does not match expected candidate")
    decision = value["decision"]
    if decision not in {"GO", "NO-GO"}:
        raise ValueError("decision must be GO or NO-GO")
    _text(value["owner_role"], "owner_role")
    classes = value["incident_classes"]
    if not isinstance(classes, list):
        raise ValueError("incident_classes must be a list")
    ids: list[str] = []
    for item in classes:
        if not isinstance(item, dict) or set(item) != KEYS:
            raise ValueError("incident class keys do not match contract")
        cid = item["id"]
        if not isinstance(cid, str):
            raise ValueError("incident class id is invalid")
        if cid in ids:
            raise ValueError(f"duplicate incident class id: {cid}")
        ids.append(cid)
        for field in ("incident_commander_role", "backup_commander_role", "severity_threshold", "user_notice_criteria", "restoration_message_process", "evidence_reference"):
            _text(item[field], f"{cid}.{field}")
        initial = _positive(item["initial_update_target_minutes"], f"{cid}.initial_update_target_minutes")
        recurring = _positive(item["recurring_update_minutes"], f"{cid}.recurring_update_minutes")
        _positive(item["post_incident_review_target_days"], f"{cid}.post_incident_review_target_days")
        if initial > recurring:
            raise ValueError(f"{cid} initial update target cannot exceed recurring cadence")
        if item["status"] not in {"VERIFIED", "NOT VERIFIED"}:
            raise ValueError(f"{cid}.status is invalid")
    missing = REQUIRED - set(ids)
    unknown = set(ids) - REQUIRED
    if missing:
        raise ValueError(f"required incident classes are missing: {sorted(missing)}")
    if unknown:
        raise ValueError(f"unknown incident classes: {sorted(unknown)}")
    if decision == "GO" and any(item["status"] != "VERIFIED" for item in classes):
        raise ValueError("GO requires every incident class VERIFIED")
    return {"candidate_sha": candidate, "incident_class_count": len(classes), "decision": decision, "result": "VALID"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("record", type=Path)
    parser.add_argument("--expected-candidate")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        value = json.loads(args.record.read_text(encoding="utf-8"))
        report = validate_record(value, args.expected_candidate)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    payload = json.dumps(report, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
