#!/usr/bin/env python3
"""Validate an append-only ledger of public-operations witness checkpoints."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SAFE_PATH = re.compile(r"^[A-Za-z0-9._/-]+$")
ZERO = "0" * 64
TOP = {"schema", "schema_version", "candidate_sha", "decision", "ledger_state", "entries"}
ENTRY = {
    "sequence", "checkpoint_path", "checkpoint_sha256", "checkpoint_digest",
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
        raise ValueError("unsafe checkpoint path")
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("unsafe checkpoint path")
    path = root / candidate
    if path.is_symlink() or not path.is_file():
        raise ValueError("checkpoint path must be a regular file")
    if root.resolve() not in path.resolve().parents:
        raise ValueError("checkpoint path escapes repository root")
    return path


def validate(
    ledger: object,
    repository_root: Path,
    expected_candidate: str | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    if not isinstance(ledger, dict) or set(ledger) != TOP:
        raise ValueError("ledger keys do not match contract")
    reject_secret_keys(ledger)
    if ledger["schema"] != "lionsforge.public-operations.witness-checkpoint-ledger" or ledger["schema_version"] != 1:
        raise ValueError("unsupported ledger schema")
    candidate = ledger["candidate_sha"]
    if not isinstance(candidate, str) or not SHA40.fullmatch(candidate):
        raise ValueError("invalid candidate_sha")
    if expected_candidate is not None and candidate != expected_candidate:
        raise ValueError("candidate drift")
    if ledger["decision"] != "NO-GO" or ledger["ledger_state"] != "VALID-NO-GO":
        raise ValueError("ledger must preserve NO-GO")
    entries = ledger["entries"]
    if not isinstance(entries, list) or not entries:
        raise ValueError("ledger entries must be non-empty")

    current = now or datetime.now(timezone.utc)
    previous_digest = ZERO
    previous_issued: datetime | None = None
    paths: set[str] = set()
    checkpoint_digests: set[str] = set()
    entry_digests: set[str] = set()

    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict) or set(entry) != ENTRY:
            raise ValueError("entry keys do not match contract")
        if entry["sequence"] != index:
            raise ValueError("checkpoint sequence gap")
        path_value = entry["checkpoint_path"]
        if not isinstance(path_value, str) or path_value in paths:
            raise ValueError("duplicate checkpoint path")
        paths.add(path_value)
        path = safe_file(repository_root, path_value)
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != require_digest(entry["checkpoint_sha256"], "checkpoint_sha256"):
            raise ValueError("checkpoint byte drift")
        try:
            checkpoint = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("malformed checkpoint JSON") from exc
        reject_secret_keys(checkpoint)
        if not isinstance(checkpoint, dict):
            raise ValueError("checkpoint must be an object")
        if checkpoint.get("schema") != "lionsforge.public-operations.witness-ledger-checkpoint":
            raise ValueError("unexpected checkpoint schema")
        if checkpoint.get("schema_version") != 1:
            raise ValueError("unexpected checkpoint schema version")
        if checkpoint.get("candidate_sha") != candidate:
            raise ValueError("checkpoint candidate drift")
        if checkpoint.get("decision") != "NO-GO" or checkpoint.get("checkpoint_state") != "VALID-NO-GO":
            raise ValueError("checkpoint state drift")
        checkpoint_digest = canonical_digest(checkpoint)
        if checkpoint_digest != require_digest(entry["checkpoint_digest"], "checkpoint_digest"):
            raise ValueError("checkpoint digest drift")
        if checkpoint_digest in checkpoint_digests:
            raise ValueError("duplicate checkpoint digest")
        checkpoint_digests.add(checkpoint_digest)
        issued = parse_time(checkpoint.get("issued_at"), "checkpoint issued_at")
        if entry["issued_at"] != checkpoint.get("issued_at"):
            raise ValueError("checkpoint issued_at drift")
        if issued > current:
            raise ValueError("future checkpoint issuance")
        expires = parse_time(checkpoint.get("expires_at"), "checkpoint expires_at")
        if expires <= current:
            raise ValueError("expired checkpoint")
        if previous_issued is not None and issued <= previous_issued:
            raise ValueError("checkpoint time regression")
        previous_issued = issued
        linked = require_digest(entry["previous_entry_digest"], "previous_entry_digest", allow_zero=True)
        if linked != previous_digest:
            raise ValueError("broken previous-entry link")
        material = {key: entry[key] for key in sorted(ENTRY) if key != "entry_digest"}
        computed_entry = canonical_digest(material)
        if computed_entry != require_digest(entry["entry_digest"], "entry_digest"):
            raise ValueError("entry digest drift")
        if computed_entry in entry_digests:
            raise ValueError("duplicate entry digest")
        entry_digests.add(computed_entry)
        previous_digest = computed_entry

    ledger_digest = canonical_digest(ledger)
    return {
        "schema": "lionsforge.public-operations.witness-checkpoint-ledger-report",
        "schema_version": 1,
        "candidate_sha": candidate,
        "decision": "NO-GO",
        "ledger_state": "VALID-NO-GO",
        "authorization": "NONE",
        "entry_count": len(entries),
        "terminal_entry_digest": previous_digest,
        "ledger_digest": ledger_digest,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ledger")
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--expected-candidate")
    parser.add_argument("--output")
    args = parser.parse_args()
    value = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
    result = validate(value, Path(args.repository_root), args.expected_candidate)
    rendered = json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
