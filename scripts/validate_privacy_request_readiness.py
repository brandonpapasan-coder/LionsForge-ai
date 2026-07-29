#!/usr/bin/env python3
"""Validate a versioned privacy-request readiness record."""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
ROLE_EMAIL_RE = re.compile(r"^[a-z0-9._%+-]+@privacy\.[a-z0-9.-]+$")
REQUIRED = {"access", "deletion", "correction", "portability", "objection-restriction", "appeal"}
TOP = {"schema", "schema_version", "candidate_sha", "decision", "owner_role", "workflows"}
WF_KEYS = {"id", "intake_contact", "owner_role", "backup_owner_role", "identity_verification", "fulfillment_path", "denial_criteria", "appeal_route", "acknowledgment_target_days", "completion_target_days", "evidence_reference", "status"}
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
    if value["schema"] != "lionsforge.privacy-request-readiness" or value["schema_version"] != 1:
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
    workflows = value["workflows"]
    if not isinstance(workflows, list):
        raise ValueError("workflows must be a list")
    ids: list[str] = []
    for workflow in workflows:
        if not isinstance(workflow, dict) or set(workflow) != WF_KEYS:
            raise ValueError("workflow keys do not match contract")
        wid = workflow["id"]
        if not isinstance(wid, str):
            raise ValueError("workflow id is invalid")
        if wid in ids:
            raise ValueError(f"duplicate workflow id: {wid}")
        ids.append(wid)
        contact = _text(workflow["intake_contact"], f"{wid}.intake_contact")
        if not ROLE_EMAIL_RE.fullmatch(contact.lower()):
            raise ValueError(f"{wid}.intake_contact must be a privacy role address")
        for field in ("owner_role", "backup_owner_role", "identity_verification", "fulfillment_path", "denial_criteria", "appeal_route", "evidence_reference"):
            _text(workflow[field], f"{wid}.{field}")
        ack = _positive(workflow["acknowledgment_target_days"], f"{wid}.acknowledgment_target_days")
        completion = _positive(workflow["completion_target_days"], f"{wid}.completion_target_days")
        if ack > completion:
            raise ValueError(f"{wid} acknowledgment target cannot exceed completion target")
        if workflow["status"] not in {"VERIFIED", "NOT VERIFIED"}:
            raise ValueError(f"{wid}.status is invalid")
    missing = REQUIRED - set(ids)
    unknown = set(ids) - REQUIRED
    if missing:
        raise ValueError(f"required workflows are missing: {sorted(missing)}")
    if unknown:
        raise ValueError(f"unknown workflows: {sorted(unknown)}")
    if len(ids) != len(REQUIRED):
        raise ValueError("workflow count is invalid")
    if decision == "GO" and any(item["status"] != "VERIFIED" for item in workflows):
        raise ValueError("GO requires every workflow to be VERIFIED")
    return {"candidate_sha": candidate, "workflow_count": len(ids), "decision": decision, "result": "VALID"}


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
    rendered = json.dumps(report, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
