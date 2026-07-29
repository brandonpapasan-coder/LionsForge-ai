#!/usr/bin/env python3
"""Validate a versioned LionsForge AI public data inventory."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PLACEHOLDERS = {"", "tbd", "todo", "pending", "unknown", "not verified", "n/a or pending"}
REQUIRED_CLASSES = {
    "account-data",
    "uploaded-evidence",
    "generated-content",
    "education-mastery-history",
    "telemetry",
    "authentication-security-logs",
    "support-privacy-records",
    "provider-bound-request-data",
    "backups",
}
TOP_KEYS = {"schema", "schema_version", "candidate_sha", "decision", "owner_role", "data_classes"}
CLASS_KEYS = {
    "id",
    "purpose",
    "storage_locations",
    "access_roles",
    "retention_rule",
    "deletion_path",
    "backup_handling",
    "subprocessors",
    "contains_personal_data",
    "contains_secrets",
    "status",
}
FORBIDDEN_KEYS = {"password", "secret", "token", "api_key", "private_key", "client_secret", "credential"}


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or value.strip().lower() in PLACEHOLDERS or len(value.strip()) < 3:
        raise ValueError(f"{label} is incomplete")
    return value.strip()


def _text_list(value: object, label: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} must be a non-empty list")
    result = [_text(item, label) for item in value]
    if len(set(result)) != len(result):
        raise ValueError(f"{label} contains duplicates")
    return result


def _reject_forbidden_keys(value: object, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized in FORBIDDEN_KEYS:
                raise ValueError(f"forbidden secret-like key at {path}.{key}")
            _reject_forbidden_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_keys(child, f"{path}[{index}]")


def validate_inventory(value: object, expected_candidate: str | None = None) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != TOP_KEYS:
        raise ValueError("inventory top-level keys are invalid")
    _reject_forbidden_keys(value)
    if value["schema"] != "lionsforge.public-data-inventory" or value["schema_version"] != 1:
        raise ValueError("inventory schema is unsupported")
    candidate = value["candidate_sha"]
    if not isinstance(candidate, str) or not SHA_RE.fullmatch(candidate):
        raise ValueError("candidate_sha must be 40 lowercase hexadecimal characters")
    if expected_candidate is not None and candidate != expected_candidate:
        raise ValueError("inventory candidate does not match expected candidate")
    decision = value["decision"]
    if decision not in {"GO", "NO-GO"}:
        raise ValueError("decision must be GO or NO-GO")
    _text(value["owner_role"], "owner_role")
    rows = value["data_classes"]
    if not isinstance(rows, list) or not rows:
        raise ValueError("data_classes must be a non-empty list")
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != CLASS_KEYS:
            raise ValueError(f"data_classes[{index}] keys are invalid")
        item_id = row["id"]
        if not isinstance(item_id, str) or not ID_RE.fullmatch(item_id):
            raise ValueError(f"data_classes[{index}].id is invalid")
        if item_id in seen:
            raise ValueError(f"duplicate data class id: {item_id}")
        seen.add(item_id)
        _text(row["purpose"], f"{item_id}.purpose")
        _text_list(row["storage_locations"], f"{item_id}.storage_locations")
        _text_list(row["access_roles"], f"{item_id}.access_roles")
        _text(row["retention_rule"], f"{item_id}.retention_rule")
        _text(row["deletion_path"], f"{item_id}.deletion_path")
        _text(row["backup_handling"], f"{item_id}.backup_handling")
        subprocessors = _text_list(row["subprocessors"], f"{item_id}.subprocessors")
        if any(item.lower() in PLACEHOLDERS for item in subprocessors):
            raise ValueError(f"{item_id}.subprocessors contains unresolved entries")
        if not isinstance(row["contains_personal_data"], bool) or not isinstance(row["contains_secrets"], bool):
            raise ValueError(f"{item_id} boolean classifications are invalid")
        if row["contains_secrets"]:
            raise ValueError(f"{item_id} must not inventory secret values")
        if row["status"] not in {"VERIFIED", "NOT VERIFIED"}:
            raise ValueError(f"{item_id}.status is invalid")
        if decision == "GO" and row["status"] != "VERIFIED":
            raise ValueError(f"GO requires VERIFIED status for {item_id}")
    missing = sorted(REQUIRED_CLASSES - seen)
    if missing:
        raise ValueError(f"required data classes are missing: {', '.join(missing)}")
    return {"candidate_sha": candidate, "decision": decision, "data_class_count": len(rows), "result": "VALID"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path)
    parser.add_argument("--expected-candidate")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        value = json.loads(args.inventory.read_text(encoding="utf-8"))
        report = validate_inventory(value, args.expected_candidate)
        if args.output:
            args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"VALID: candidate={report['candidate_sha']} classes={report['data_class_count']} decision={report['decision']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
