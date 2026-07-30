#!/usr/bin/env python3
"""Validate an append-only ledger of checkpoint-ledger witness receipts."""
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
    "sequence", "witness_path", "witness_sha256", "witness_digest", "checkpoint_ledger_digest",
    "entry_count", "terminal_entry_digest", "witness_receipt_id", "witness_role", "witness_key_id",
    "signature_algorithm", "signature_sha256", "nonce_sha256", "issued_at", "expires_at",
    "previous_entry_digest", "entry_digest",
}
SOURCE = {
    "schema", "schema_version", "candidate_sha", "decision", "witness_state",
    "checkpoint_ledger_path", "checkpoint_ledger_sha256", "checkpoint_ledger_digest",
    "entry_count", "terminal_entry_digest", "witness_receipt_id", "witness_role",
    "witness_key_id", "signature_algorithm", "signature_sha256", "nonce_sha256",
    "issued_at", "expires_at",
}
FORBIDDEN = ("password", "secret", "token", "api_key", "private_key", "credential")


def canonical_digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def require_digest(value: object, name: str, *, allow_zero: bool = False) -> str:
    if not isinstance(value, str) or not SHA256.fullmatch(value) or (not allow_zero and value == ZERO):
        raise ValueError(f"invalid {name}")
    return value


def parse_time(value: object, name: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError(f"{name} must be RFC3339 UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{name} must be RFC3339 UTC") from exc
    return parsed


def safe_file(root: Path, relative: object) -> Path:
    if not isinstance(relative, str) or not SAFE_PATH.fullmatch(relative):
        raise ValueError("unsafe witness path")
    if relative.startswith("/") or ".." in Path(relative).parts:
        raise ValueError("unsafe witness path")
    resolved_root = root.resolve()
    path = (resolved_root / relative).resolve()
    if resolved_root not in path.parents or not path.is_file() or path.is_symlink():
        raise ValueError("invalid witness source file")
    return path


def reject_secret_keys(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).lower()
            if any(fragment in lowered for fragment in FORBIDDEN):
                raise ValueError("secret-like key rejected")
            reject_secret_keys(item)
    elif isinstance(value, list):
        for item in value:
            reject_secret_keys(item)


def validate(data: object, repository_root: Path, expected_candidate: str | None = None,
             *, now: datetime | None = None) -> dict[str, object]:
    if not isinstance(data, dict) or set(data) != TOP:
        raise ValueError("invalid witness ledger keys")
    reject_secret_keys(data)
    if data["schema"] != "lionsforge.public-operations-checkpoint-ledger-witness-ledger" or data["schema_version"] != 1:
        raise ValueError("unsupported witness ledger schema")
    candidate = data["candidate_sha"]
    if not isinstance(candidate, str) or not SHA40.fullmatch(candidate):
        raise ValueError("invalid candidate_sha")
    if expected_candidate and candidate != expected_candidate:
        raise ValueError("candidate mismatch")
    if data["decision"] != "NO-GO" or data["ledger_state"] != "VALID-NO-GO":
        raise ValueError("witness ledger must preserve NO-GO")
    entries = data["entries"]
    if not isinstance(entries, list) or not entries or len(entries) > 225:
        raise ValueError("entries must contain 1..225 records")

    root = repository_root.resolve()
    previous = ZERO
    last_issued: datetime | None = None
    seen_paths: set[str] = set()
    seen_ids: set[str] = set()
    seen_witnesses: set[str] = set()
    seen_nonces: set[str] = set()
    stable_identity: tuple[object, object, object] | None = None
    current = now or datetime.now(timezone.utc)

    for expected_sequence, entry in enumerate(entries, 1):
        if not isinstance(entry, dict) or set(entry) != ENTRY:
            raise ValueError("invalid witness ledger entry keys")
        if entry["sequence"] != expected_sequence:
            raise ValueError("witness sequence gap")
        path_text = entry["witness_path"]
        if path_text in seen_paths:
            raise ValueError("duplicate witness path")
        path = safe_file(root, path_text)
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != require_digest(entry["witness_sha256"], "witness_sha256"):
            raise ValueError("witness source byte drift")
        try:
            source = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("malformed witness source JSON") from exc
        if not isinstance(source, dict) or set(source) != SOURCE:
            raise ValueError("invalid witness source keys")
        reject_secret_keys(source)
        if source["schema"] != "lionsforge.public-operations-checkpoint-ledger-witness" or source["schema_version"] != 1:
            raise ValueError("unsupported witness source schema")
        if source["candidate_sha"] != candidate:
            raise ValueError("witness source candidate drift")
        if source["decision"] != "NO-GO" or source["witness_state"] != "VALID-NO-GO":
            raise ValueError("witness source state drift")

        fields = (
            "checkpoint_ledger_digest", "entry_count", "terminal_entry_digest", "witness_receipt_id",
            "witness_role", "witness_key_id", "signature_algorithm", "signature_sha256", "nonce_sha256",
            "issued_at", "expires_at",
        )
        for field in fields:
            if entry[field] != source[field]:
                raise ValueError(f"{field} drift")
        witness_digest = canonical_digest(source)
        if entry["witness_digest"] != witness_digest:
            raise ValueError("witness digest drift")
        for name in ("witness_digest", "checkpoint_ledger_digest", "terminal_entry_digest", "signature_sha256", "nonce_sha256"):
            require_digest(entry[name], name)
        if entry["witness_receipt_id"] in seen_ids:
            raise ValueError("duplicate witness receipt id")
        if witness_digest in seen_witnesses:
            raise ValueError("duplicate witness digest")
        if entry["nonce_sha256"] in seen_nonces:
            raise ValueError("duplicate witness nonce")
        identity = (entry["witness_role"], entry["witness_key_id"], entry["signature_algorithm"])
        if stable_identity is None:
            stable_identity = identity
        elif identity != stable_identity:
            raise ValueError("witness identity drift")
        issued = parse_time(entry["issued_at"], "issued_at")
        expires = parse_time(entry["expires_at"], "expires_at")
        if expires <= issued or expires <= current:
            raise ValueError("expired or invalid witness receipt")
        if last_issued and issued <= last_issued:
            raise ValueError("non-monotonic witness issuance")
        if entry["previous_entry_digest"] != previous:
            raise ValueError("broken previous-entry link")
        material = {name: entry[name] for name in ENTRY - {"entry_digest"}}
        if entry["entry_digest"] != canonical_digest(material):
            raise ValueError("invalid witness ledger entry digest")

        seen_paths.add(path_text)
        seen_ids.add(entry["witness_receipt_id"])
        seen_witnesses.add(witness_digest)
        seen_nonces.add(entry["nonce_sha256"])
        last_issued = issued
        previous = entry["entry_digest"]

    result = {
        "schema": "lionsforge.public-operations-checkpoint-ledger-witness-ledger-report",
        "schema_version": 1,
        "candidate_sha": candidate,
        "decision": "NO-GO",
        "ledger_state": "VALID-NO-GO",
        "entry_count": len(entries),
        "terminal_entry_digest": previous,
        "witness_ledger_digest": canonical_digest(data),
        "authorization": "NONE",
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("ledger")
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--expected-candidate")
    parser.add_argument("--output")
    args = parser.parse_args()
    ledger_path = Path(args.ledger)
    result = validate(json.loads(ledger_path.read_text()), Path(args.repository_root), args.expected_candidate)
    rendered = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
