#!/usr/bin/env python3
"""Validate an append-only ledger of operational-readiness snapshots."""
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
TOP = {"schema", "schema_version", "candidate_sha", "decision", "ledger_state", "entries"}
ENTRY = {
    "sequence", "snapshot_path", "snapshot_sha256", "snapshot_digest",
    "issued_at", "previous_entry_digest", "entry_digest",
}
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


def require_digest(value: object, name: str, *, allow_zero: bool = False) -> str:
    if not isinstance(value, str) or not SHA256.fullmatch(value) or (value == ZERO and not allow_zero):
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
        raise ValueError("unsafe snapshot path")
    if relative.startswith("/") or ".." in Path(relative).parts:
        raise ValueError("unsafe snapshot path")
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise ValueError("snapshot path must be a regular file")
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("snapshot path escapes repository root") from exc
    return path


def validate(value: object, root: Path, expected_candidate: str | None = None, *, now: datetime | None = None) -> dict[str, object]:
    now = now or datetime.now(timezone.utc)
    if not isinstance(value, dict) or set(value) != TOP:
        raise ValueError("invalid ledger keys")
    reject_secret_keys(value)
    if value["schema"] != "lionsforge.operational-readiness.snapshot-ledger" or value["schema_version"] != 1:
        raise ValueError("unsupported ledger schema")
    candidate = value["candidate_sha"]
    if not isinstance(candidate, str) or not SHA40.fullmatch(candidate):
        raise ValueError("invalid candidate SHA")
    if expected_candidate and candidate != expected_candidate:
        raise ValueError("candidate mismatch")
    if value["decision"] != "NO-GO" or value["ledger_state"] != "VALID-NO-GO":
        raise ValueError("ledger must preserve NO-GO and VALID-NO-GO")
    entries = value["entries"]
    if not isinstance(entries, list) or not entries:
        raise ValueError("ledger entries must be non-empty")

    previous = ZERO
    previous_time: datetime | None = None
    paths: set[str] = set()
    snapshots: set[str] = set()
    entry_digests: set[str] = set()
    normalized: list[dict[str, object]] = []

    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict) or set(entry) != ENTRY:
            raise ValueError("invalid entry keys")
        if entry["sequence"] != index:
            raise ValueError("sequence gap")
        path_text = entry["snapshot_path"]
        path = safe_file(root, path_text)
        if path_text in paths:
            raise ValueError("duplicate snapshot path")
        paths.add(path_text)
        raw = path.read_bytes()
        source_sha = hashlib.sha256(raw).hexdigest()
        if require_digest(entry["snapshot_sha256"], "snapshot SHA-256") != source_sha:
            raise ValueError("snapshot byte drift")
        try:
            snapshot = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("malformed snapshot JSON") from exc
        if not isinstance(snapshot, dict):
            raise ValueError("snapshot must be an object")
        reject_secret_keys(snapshot)
        snapshot_digest = canonical_digest(snapshot)
        if require_digest(entry["snapshot_digest"], "snapshot digest") != snapshot_digest:
            raise ValueError("snapshot digest drift")
        if snapshot_digest in snapshots:
            raise ValueError("duplicate snapshot identity")
        snapshots.add(snapshot_digest)
        if snapshot.get("candidate_sha") != candidate:
            raise ValueError("snapshot candidate drift")
        if snapshot.get("readiness_state") != "VALID-NO-GO":
            raise ValueError("snapshot state drift")
        if snapshot.get("authorization") != "NONE":
            raise ValueError("snapshot authorization must be NONE")
        issued_at = parse_time(entry["issued_at"], "entry issued_at")
        if snapshot.get("issued_at") != entry["issued_at"]:
            raise ValueError("issue-time drift")
        expires_at = parse_time(snapshot.get("expires_at"), "snapshot expires_at")
        if issued_at > now:
            raise ValueError("future snapshot")
        if expires_at <= now:
            raise ValueError("expired snapshot")
        if previous_time is not None and issued_at <= previous_time:
            raise ValueError("time regression")
        previous_time = issued_at
        if require_digest(entry["previous_entry_digest"], "previous entry digest", allow_zero=index == 1) != previous:
            raise ValueError("broken previous-entry link")
        without_digest = {key: item for key, item in entry.items() if key != "entry_digest"}
        computed = canonical_digest(without_digest)
        if require_digest(entry["entry_digest"], "entry digest") != computed:
            raise ValueError("entry digest drift")
        if computed in entry_digests:
            raise ValueError("duplicate entry digest")
        entry_digests.add(computed)
        previous = computed
        normalized.append(dict(entry))

    ledger_digest = canonical_digest({key: value[key] for key in sorted(TOP - {"entries"})} | {"entries": normalized})
    return {
        "schema": "lionsforge.operational-readiness.snapshot-ledger-report",
        "schema_version": 1,
        "candidate_sha": candidate,
        "decision": "NO-GO",
        "ledger_state": "VALID-NO-GO",
        "authorization": "NONE",
        "entry_count": len(entries),
        "terminal_entry_digest": previous,
        "ledger_digest": ledger_digest,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    parser.add_argument("--expected-candidate")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        value = json.loads(args.ledger.read_text(encoding="utf-8"))
        result = validate(value, args.repository_root, args.expected_candidate)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
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
