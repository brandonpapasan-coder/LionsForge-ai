#!/usr/bin/env python3
"""Validate a versioned public support and escalation readiness record."""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
ROLE_EMAIL_RE = re.compile(r"^[a-z0-9._%+-]+@(support|privacy|security|abuse)\.[a-z0-9.-]+$")
REQUIRED = {"general-support", "privacy-requests", "security-reports", "abuse-reports"}
TOP = {"schema","schema_version","candidate_sha","decision","owner_role","channels"}
CH_KEYS = {"id","public_contact","owner_role","backup_owner_role","monitored_schedule","acknowledgment_target_minutes","resolution_target_hours","critical_escalation_minutes","escalation_role","after_hours_coverage","test_evidence_reference","status"}
PLACEHOLDERS = {"","TBD","TODO","PENDING","NOT VERIFIED","UNKNOWN","N/A"}
FORBIDDEN = ("password","secret","token","api_key","private_key","credential")

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
        for item in value: _scan(item)

def validate_record(value: object, expected_candidate: str | None = None) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != TOP:
        raise ValueError("top-level keys do not match contract")
    _scan(value)
    if value["schema"] != "lionsforge.support-escalation-readiness" or value["schema_version"] != 1:
        raise ValueError("schema is invalid")
    candidate = value["candidate_sha"]
    if not isinstance(candidate, str) or not SHA_RE.fullmatch(candidate):
        raise ValueError("candidate_sha is invalid")
    if expected_candidate and candidate != expected_candidate:
        raise ValueError("candidate does not match expected candidate")
    decision = value["decision"]
    if decision not in {"GO","NO-GO"}: raise ValueError("decision must be GO or NO-GO")
    _text(value["owner_role"], "owner_role")
    channels = value["channels"]
    if not isinstance(channels, list): raise ValueError("channels must be a list")
    ids: list[str] = []
    for channel in channels:
        if not isinstance(channel, dict) or set(channel) != CH_KEYS:
            raise ValueError("channel keys do not match contract")
        cid = channel["id"]
        if not isinstance(cid, str): raise ValueError("channel id is invalid")
        if cid in ids: raise ValueError(f"duplicate channel id: {cid}")
        ids.append(cid)
        contact = _text(channel["public_contact"], f"{cid}.public_contact")
        if not ROLE_EMAIL_RE.fullmatch(contact.lower()):
            raise ValueError(f"{cid}.public_contact must be a role address on a channel subdomain")
        for field in ("owner_role","backup_owner_role","monitored_schedule","escalation_role","after_hours_coverage","test_evidence_reference"):
            _text(channel[field], f"{cid}.{field}")
        ack = _positive(channel["acknowledgment_target_minutes"], f"{cid}.acknowledgment_target_minutes")
        critical = _positive(channel["critical_escalation_minutes"], f"{cid}.critical_escalation_minutes")
        resolution = _positive(channel["resolution_target_hours"], f"{cid}.resolution_target_hours")
        if critical > ack: raise ValueError(f"{cid}.critical escalation cannot be slower than acknowledgment")
        if ack > resolution * 60: raise ValueError(f"{cid}.acknowledgment cannot exceed resolution target")
        if channel["status"] not in {"VERIFIED","NOT VERIFIED"}: raise ValueError(f"{cid}.status is invalid")
    missing = REQUIRED - set(ids)
    if missing: raise ValueError(f"required channels are missing: {', '.join(sorted(missing))}")
    if set(ids) - REQUIRED: raise ValueError("unknown channel ids are not permitted")
    if decision == "GO" and any(c["status"] != "VERIFIED" for c in channels):
        raise ValueError("GO requires every channel to be VERIFIED")
    return {"candidate_sha": candidate, "channel_count": len(channels), "decision": decision, "result": "VALID"}

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    parser.add_argument("--expected-candidate")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        value = json.loads(args.record.read_text(encoding="utf-8"))
        report = validate_record(value, args.expected_candidate)
        if args.output:
            args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr); return 1
    print("VALID: support and escalation readiness record is structurally complete")
    return 0
if __name__ == "__main__": raise SystemExit(main())
