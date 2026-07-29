#!/usr/bin/env python3
"""Validate and cryptographically bind public-operations readiness evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
SAFE_PATH_RE = re.compile(r"^[A-Za-z0-9._/-]+$")
REQUIRED = {
    "public-data-inventory",
    "support-escalation-readiness",
    "privacy-request-readiness",
    "incident-communication-readiness",
}
TOP = {"schema", "schema_version", "candidate_sha", "decision", "owner_role", "evidence"}
ITEM_KEYS = {"type", "path", "sha256", "required_decision"}
FORBIDDEN = ("password", "secret", "token", "api_key", "private_key", "credential")


def _scan(value: object) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if any(term in key.lower() for term in FORBIDDEN):
                raise ValueError(f"forbidden secret-like key: {key}")
            _scan(nested)
    elif isinstance(value, list):
        for item in value:
            _scan(item)


def _safe_path(value: object) -> str:
    if not isinstance(value, str) or not SAFE_PATH_RE.fullmatch(value):
        raise ValueError("evidence path is invalid")
    if value.startswith("/") or ".." in value.split("/"):
        raise ValueError("evidence path is unsafe")
    return value


def validate_structure(value: object, expected_candidate: str | None = None) -> list[dict[str, str]]:
    if not isinstance(value, dict) or set(value) != TOP:
        raise ValueError("top-level keys do not match contract")
    _scan(value)
    if value["schema"] != "lionsforge.public-operations-evidence-manifest" or value["schema_version"] != 1:
        raise ValueError("schema is invalid")
    candidate = value["candidate_sha"]
    if not isinstance(candidate, str) or not SHA_RE.fullmatch(candidate):
        raise ValueError("candidate_sha is invalid")
    if expected_candidate and candidate != expected_candidate:
        raise ValueError("candidate does not match expected candidate")
    if value["decision"] not in {"GO", "NO-GO"}:
        raise ValueError("decision must be GO or NO-GO")
    if not isinstance(value["owner_role"], str) or len(value["owner_role"].strip()) < 3:
        raise ValueError("owner_role is incomplete")
    evidence = value["evidence"]
    if not isinstance(evidence, list):
        raise ValueError("evidence must be a list")
    seen: set[str] = set()
    normalized: list[dict[str, str]] = []
    for item in evidence:
        if not isinstance(item, dict) or set(item) != ITEM_KEYS:
            raise ValueError("evidence keys do not match contract")
        evidence_type = item["type"]
        if evidence_type not in REQUIRED:
            raise ValueError("evidence type is invalid")
        if evidence_type in seen:
            raise ValueError(f"duplicate evidence type: {evidence_type}")
        seen.add(evidence_type)
        path = _safe_path(item["path"])
        digest = item["sha256"]
        if not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest):
            raise ValueError("sha256 is invalid")
        required_decision = item["required_decision"]
        if required_decision not in {"GO", "NO-GO"}:
            raise ValueError("required_decision is invalid")
        normalized.append({"type": evidence_type, "path": path, "sha256": digest, "required_decision": required_decision})
    missing = REQUIRED - seen
    if missing:
        raise ValueError(f"required evidence types are missing: {sorted(missing)}")
    if value["decision"] == "GO" and any(item["required_decision"] != "GO" for item in normalized):
        raise ValueError("GO requires every evidence record to require GO")
    return sorted(normalized, key=lambda item: item["type"])


def validate_manifest(value: object, repository_root: Path, expected_candidate: str | None = None) -> dict[str, object]:
    items = validate_structure(value, expected_candidate)
    candidate = value["candidate_sha"]
    aggregate = hashlib.sha256()
    for item in items:
        path = repository_root / item["path"]
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"evidence file is missing or unsafe: {item['path']}")
        payload = path.read_bytes()
        actual = hashlib.sha256(payload).hexdigest()
        if actual != item["sha256"]:
            raise ValueError(f"evidence digest mismatch: {item['type']}")
        record = json.loads(payload)
        if record.get("candidate_sha") != candidate:
            raise ValueError(f"evidence candidate mismatch: {item['type']}")
        if record.get("decision") != item["required_decision"]:
            raise ValueError(f"evidence decision mismatch: {item['type']}")
        aggregate.update(f"{item['type']}:{actual}\n".encode())
    return {
        "aggregate_evidence_sha256": aggregate.hexdigest(),
        "candidate_sha": candidate,
        "decision": value["decision"],
        "evidence_count": len(items),
        "result": "VALID",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    parser.add_argument("--expected-candidate")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        value = json.loads(args.manifest.read_text(encoding="utf-8"))
        report = validate_manifest(value, args.repository_root.resolve(), args.expected_candidate)
        rendered = json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n"
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        sys.stdout.write(rendered)
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"invalid public operations evidence manifest: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
