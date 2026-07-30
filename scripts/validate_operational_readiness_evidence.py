#!/usr/bin/env python3
"""Validate and aggregate non-secret operational-readiness evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SAFE_PATH = re.compile(r"^[A-Za-z0-9._/-]+$")
ZERO = "0" * 64
TOP = {"schema", "schema_version", "candidate_sha", "decision", "readiness_state", "evidence"}
ENTRY = {"evidence_type", "report_path", "report_sha256", "report_digest", "issued_at", "expires_at"}
STATE_KEYS = ("readiness_state", "ledger_state", "checkpoint_state", "validation_state", "state")
FORBIDDEN = ("password", "secret", "token", "api_key", "private_key", "credential")


def canonical_digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def parse_time(value: object, name: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{name} must be RFC3339 UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be RFC3339 UTC") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{name} must be timezone aware")
    return parsed


def require_digest(value: object, name: str) -> str:
    if not isinstance(value, str) or not SHA256.fullmatch(value) or value == ZERO:
        raise ValueError(f"invalid {name}")
    return value


def reject_secret_keys(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if any(marker in str(key).lower() for marker in FORBIDDEN):
                raise ValueError("secret-like key is forbidden")
            reject_secret_keys(item)
    elif isinstance(value, list):
        for item in value:
            reject_secret_keys(item)


def safe_file(root: Path, relative: object) -> Path:
    if not isinstance(relative, str) or not SAFE_PATH.fullmatch(relative):
        raise ValueError("unsafe report path")
    if relative.startswith("/") or ".." in Path(relative).parts:
        raise ValueError("unsafe report path")
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise ValueError("report path must be a regular file")
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("report path escapes repository root") from exc
    return path


def report_state(report: dict[str, object]) -> str:
    found = [report[key] for key in STATE_KEYS if key in report]
    if len(found) != 1 or found[0] != "VALID-NO-GO":
        raise ValueError("report must contain exactly one VALID-NO-GO state")
    return str(found[0])


def validate(
    manifest: object,
    root: Path,
    expected_candidate: str | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    if not isinstance(manifest, dict) or set(manifest) != TOP:
        raise ValueError("invalid manifest keys")
    reject_secret_keys(manifest)
    if manifest["schema"] != "lionsforge.operational-readiness.evidence-manifest":
        raise ValueError("invalid schema")
    if manifest["schema_version"] != 1:
        raise ValueError("unsupported schema version")
    candidate = manifest["candidate_sha"]
    if not isinstance(candidate, str) or not SHA40.fullmatch(candidate):
        raise ValueError("invalid candidate SHA")
    if expected_candidate is not None and candidate != expected_candidate:
        raise ValueError("candidate mismatch")
    if manifest["decision"] != "NO-GO" or manifest["readiness_state"] != "VALID-NO-GO":
        raise ValueError("manifest must preserve NO-GO and VALID-NO-GO")
    entries = manifest["evidence"]
    if not isinstance(entries, list) or not entries or len(entries) > 64:
        raise ValueError("evidence must contain 1..64 entries")

    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError("now must be timezone aware")
    seen_types: set[str] = set()
    seen_paths: set[str] = set()
    seen_sha: set[str] = set()
    seen_digests: set[str] = set()
    normalized: list[dict[str, object]] = []

    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != ENTRY:
            raise ValueError("invalid evidence entry keys")
        evidence_type = entry["evidence_type"]
        if not isinstance(evidence_type, str) or not re.fullmatch(r"[a-z][a-z0-9-]{2,63}", evidence_type):
            raise ValueError("invalid evidence type")
        path_text = entry["report_path"]
        report_sha = require_digest(entry["report_sha256"], "report SHA-256")
        declared_digest = require_digest(entry["report_digest"], "report digest")
        issued = parse_time(entry["issued_at"], "issued_at")
        expires = parse_time(entry["expires_at"], "expires_at")
        if issued > current:
            raise ValueError("future evidence issuance")
        if expires <= issued or expires <= current:
            raise ValueError("expired evidence")
        path = safe_file(root, path_text)
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != report_sha:
            raise ValueError("report byte drift")
        try:
            report = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("malformed report JSON") from exc
        if not isinstance(report, dict):
            raise ValueError("report must be a JSON object")
        reject_secret_keys(report)
        if report.get("candidate_sha") != candidate:
            raise ValueError("report candidate drift")
        if report.get("authorization") != "NONE":
            raise ValueError("report authorization must be NONE")
        report_state(report)
        if canonical_digest(report) != declared_digest:
            raise ValueError("report digest drift")
        if report.get("issued_at") not in (None, entry["issued_at"]):
            raise ValueError("report issue-time drift")
        if report.get("expires_at") not in (None, entry["expires_at"]):
            raise ValueError("report expiration drift")
        if evidence_type in seen_types or path_text in seen_paths or report_sha in seen_sha or declared_digest in seen_digests:
            raise ValueError("duplicate evidence identity")
        seen_types.add(evidence_type)
        seen_paths.add(str(path_text))
        seen_sha.add(report_sha)
        seen_digests.add(declared_digest)
        normalized.append({
            "evidence_type": evidence_type,
            "report_path": path_text,
            "report_sha256": report_sha,
            "report_digest": declared_digest,
            "issued_at": entry["issued_at"],
            "expires_at": entry["expires_at"],
            "state": "VALID-NO-GO",
        })

    normalized.sort(key=lambda item: str(item["evidence_type"]))
    evidence_digest = canonical_digest(normalized)
    snapshot = {
        "schema": "lionsforge.operational-readiness.snapshot",
        "schema_version": 1,
        "candidate_sha": candidate,
        "decision": "NO-GO",
        "readiness_state": "VALID-NO-GO",
        "authorization": "NONE",
        "evidence_count": len(normalized),
        "evidence_types": [item["evidence_type"] for item in normalized],
        "evidence_digest": evidence_digest,
        "manifest_digest": canonical_digest(manifest),
    }
    snapshot["snapshot_digest"] = canonical_digest(snapshot)
    return snapshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    parser.add_argument("--expected-candidate")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        result = validate(manifest, args.repository_root, args.expected_candidate)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    rendered = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
