#!/usr/bin/env python3
"""Validate an append-only public-operations checkpoint ledger."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SAFE_PATH = re.compile(r"^[A-Za-z0-9._/-]+$")
KEY_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{7,127}$")
ZERO = "0" * 64
TOP = {"schema", "schema_version", "candidate_sha", "decision", "ledger_state", "entries"}
ENTRY = {
    "checkpoint_sequence", "checkpoint_path", "checkpoint_sha256", "checkpoint_digest",
    "ledger_digest", "entry_count", "terminal_entry_digest", "signer_role", "key_id",
    "signature_algorithm", "signature_sha256", "issued_at", "previous_entry_digest", "entry_digest",
}
ALGORITHMS = {"ed25519-sha256", "ecdsa-p256-sha256"}
FORBIDDEN = ("password", "secret", "token", "api_key", "private_key", "credential")


def canonical_digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def parse_time(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("issued_at must be RFC3339 UTC")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("issued_at must be RFC3339 UTC") from exc


def require_digest(value: object, name: str, *, allow_zero: bool = False) -> str:
    if not isinstance(value, str) or not SHA256.fullmatch(value) or (not allow_zero and value == ZERO):
        raise ValueError(f"invalid {name}")
    return value


def safe_file(root: Path, relative: object) -> Path:
    if not isinstance(relative, str) or not SAFE_PATH.fullmatch(relative):
        raise ValueError("unsafe checkpoint path")
    if relative.startswith("/") or ".." in Path(relative).parts:
        raise ValueError("unsafe checkpoint path")
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise ValueError("checkpoint file missing or symlinked")
    return path


def validate(ledger: dict[str, object], root: Path, expected_candidate: str | None = None) -> dict[str, object]:
    if set(ledger) != TOP:
        raise ValueError("invalid top-level keys")
    if any(term in str(key).lower() for key in ledger for term in FORBIDDEN):
        raise ValueError("secret-like key detected")
    if ledger["schema"] != "lionsforge.public-operations-checkpoint-ledger" or ledger["schema_version"] != 1:
        raise ValueError("unsupported schema")
    candidate = ledger["candidate_sha"]
    if not isinstance(candidate, str) or not SHA40.fullmatch(candidate):
        raise ValueError("invalid candidate SHA")
    if expected_candidate and candidate != expected_candidate:
        raise ValueError("expected candidate mismatch")
    if ledger["decision"] != "NO-GO" or ledger["ledger_state"] != "VALID-NO-GO":
        raise ValueError("ledger must remain VALID-NO-GO")
    entries = ledger["entries"]
    if not isinstance(entries, list) or not entries or len(entries) > 1000:
        raise ValueError("entries must contain 1..1000 records")

    checkpoint_digests: set[str] = set()
    paths: set[str] = set()
    previous = ZERO
    prior_time: datetime | None = None
    signer_role: str | None = None
    key_id: str | None = None
    algorithm: str | None = None

    for sequence, raw in enumerate(entries, start=1):
        if not isinstance(raw, dict) or set(raw) != ENTRY:
            raise ValueError("invalid entry keys")
        if any(term in str(key).lower() for key in raw for term in FORBIDDEN):
            raise ValueError("secret-like key detected")
        if raw["checkpoint_sequence"] != sequence:
            raise ValueError("checkpoint sequence gap")
        path_value = raw["checkpoint_path"]
        path = safe_file(root, path_value)
        if path_value in paths:
            raise ValueError("duplicate checkpoint path")
        paths.add(path_value)
        source_bytes = path.read_bytes()
        if hashlib.sha256(source_bytes).hexdigest() != require_digest(raw["checkpoint_sha256"], "checkpoint_sha256"):
            raise ValueError("checkpoint SHA drift")
        try:
            source = json.loads(source_bytes)
        except json.JSONDecodeError as exc:
            raise ValueError("malformed source checkpoint") from exc
        if not isinstance(source, dict):
            raise ValueError("malformed source checkpoint")
        expected_fields = {
            "candidate_sha": candidate,
            "decision": "NO-GO",
            "checkpoint_state": "VALID-NO-GO",
            "checkpoint_sequence": raw["checkpoint_sequence"],
            "ledger_digest": raw["ledger_digest"],
            "entry_count": raw["entry_count"],
            "terminal_entry_digest": raw["terminal_entry_digest"],
            "signer_role": raw["signer_role"],
            "key_id": raw["key_id"],
            "signature_algorithm": raw["signature_algorithm"],
            "signature_sha256": raw["signature_sha256"],
            "issued_at": raw["issued_at"],
        }
        for name, value in expected_fields.items():
            if source.get(name) != value:
                raise ValueError(f"{name} drift")
        checkpoint_digest = require_digest(raw["checkpoint_digest"], "checkpoint_digest")
        if checkpoint_digest in checkpoint_digests:
            raise ValueError("duplicate checkpoint digest")
        checkpoint_digests.add(checkpoint_digest)
        if source.get("checkpoint_digest") not in (None, checkpoint_digest):
            raise ValueError("checkpoint_digest drift")
        require_digest(raw["ledger_digest"], "ledger_digest")
        require_digest(raw["terminal_entry_digest"], "terminal_entry_digest")
        require_digest(raw["signature_sha256"], "signature_sha256")
        if not isinstance(raw["entry_count"], int) or isinstance(raw["entry_count"], bool) or raw["entry_count"] < 1:
            raise ValueError("invalid entry_count")
        if raw["signer_role"] != "independent-checkpoint-signer":
            raise ValueError("invalid signer role")
        if not isinstance(raw["key_id"], str) or not KEY_ID.fullmatch(raw["key_id"]):
            raise ValueError("invalid key ID")
        if raw["signature_algorithm"] not in ALGORITHMS:
            raise ValueError("unsupported signature algorithm")
        if signer_role is None:
            signer_role, key_id, algorithm = raw["signer_role"], raw["key_id"], raw["signature_algorithm"]
        elif (raw["signer_role"], raw["key_id"], raw["signature_algorithm"]) != (signer_role, key_id, algorithm):
            raise ValueError("signer/key/algorithm drift")
        issued = parse_time(raw["issued_at"])
        if prior_time is not None and issued <= prior_time:
            raise ValueError("issued_at must increase monotonically")
        prior_time = issued
        previous_field = require_digest(raw["previous_entry_digest"], "previous_entry_digest", allow_zero=True)
        if previous_field != previous:
            raise ValueError("broken previous-entry link")
        material = {name: raw[name] for name in ENTRY - {"entry_digest"}}
        entry_digest = require_digest(raw["entry_digest"], "entry_digest")
        if entry_digest != canonical_digest(material):
            raise ValueError("invalid entry digest")
        previous = entry_digest

    report_material = {
        "schema": ledger["schema"],
        "schema_version": ledger["schema_version"],
        "candidate_sha": candidate,
        "decision": "NO-GO",
        "ledger_state": "VALID-NO-GO",
        "entry_count": len(entries),
        "terminal_entry_digest": previous,
        "authorization": "NONE",
    }
    return {**report_material, "checkpoint_ledger_digest": canonical_digest(report_material)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ledger")
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--expected-candidate")
    parser.add_argument("--output")
    args = parser.parse_args()
    path = Path(args.ledger)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("ledger must be an object")
        report = validate(data, Path(args.repository_root).resolve(), args.expected_candidate)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    encoded = json.dumps(report, sort_keys=True, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
