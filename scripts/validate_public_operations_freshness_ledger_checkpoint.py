#!/usr/bin/env python3
"""Validate one rollback-resistant public-operations freshness ledger checkpoint."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
KEY_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{7,127}$")
SAFE_PATH = re.compile(r"^[A-Za-z0-9._/-]+$")
ZERO = "0" * 64
ALGORITHMS = {"ed25519-sha256", "ecdsa-p256-sha256"}
TOP = {
    "schema", "schema_version", "candidate_sha", "decision", "checkpoint_state",
    "ledger_path", "ledger_sha256", "ledger_digest", "entry_count",
    "terminal_entry_digest", "checkpoint_sequence", "previous_checkpoint_digest",
    "signer_role", "key_id", "signature_algorithm", "signature_sha256", "issued_at",
}
FORBIDDEN = ("password", "secret", "token", "api_key", "private_key", "credential")


def canonical_digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def parse_time(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("issued_at must be RFC3339 UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("issued_at must be RFC3339 UTC") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("issued_at must be UTC")
    return parsed


def safe_file(root: Path, relative: object) -> Path:
    if not isinstance(relative, str) or not SAFE_PATH.fullmatch(relative):
        raise ValueError("unsafe ledger path")
    if relative.startswith("/") or ".." in Path(relative).parts:
        raise ValueError("unsafe ledger path")
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise ValueError("ledger file missing or symlinked")
    return path


def require_digest(value: object, name: str, *, allow_zero: bool = False) -> str:
    if not isinstance(value, str) or not SHA256.fullmatch(value) or (not allow_zero and value == ZERO):
        raise ValueError(f"invalid {name}")
    return value


def validate(
    checkpoint: dict[str, object],
    root: Path,
    expected_candidate: str | None = None,
    minimum_sequence: int | None = None,
    expected_previous: str | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    if set(checkpoint) != TOP:
        raise ValueError("invalid top-level keys")
    if any(term in str(key).lower() for key in checkpoint for term in FORBIDDEN):
        raise ValueError("secret-like key detected")
    if checkpoint["schema"] != "lionsforge.public-operations-freshness-ledger-checkpoint" or checkpoint["schema_version"] != 1:
        raise ValueError("unsupported schema")

    candidate = checkpoint["candidate_sha"]
    if not isinstance(candidate, str) or not SHA40.fullmatch(candidate):
        raise ValueError("invalid candidate SHA")
    if expected_candidate and candidate != expected_candidate:
        raise ValueError("expected candidate mismatch")
    if checkpoint["decision"] != "NO-GO" or checkpoint["checkpoint_state"] != "VALID-NO-GO":
        raise ValueError("checkpoint must remain VALID-NO-GO")

    ledger_sha = require_digest(checkpoint["ledger_sha256"], "ledger digest")
    ledger_digest = require_digest(checkpoint["ledger_digest"], "ledger report digest")
    terminal = require_digest(checkpoint["terminal_entry_digest"], "terminal entry digest")
    previous = require_digest(checkpoint["previous_checkpoint_digest"], "previous checkpoint digest", allow_zero=True)
    signature = require_digest(checkpoint["signature_sha256"], "signature digest")
    if len({ledger_sha, ledger_digest, terminal, signature}) != 4:
        raise ValueError("checkpoint digests must be distinct")

    sequence = checkpoint["checkpoint_sequence"]
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        raise ValueError("invalid checkpoint sequence")
    if minimum_sequence is not None and sequence <= minimum_sequence:
        raise ValueError("checkpoint sequence rollback")
    if sequence == 1 and previous != ZERO:
        raise ValueError("first checkpoint must use zero previous digest")
    if sequence > 1 and previous == ZERO:
        raise ValueError("subsequent checkpoint requires previous digest")
    if expected_previous is not None and previous != expected_previous:
        raise ValueError("broken checkpoint link")

    entry_count = checkpoint["entry_count"]
    if not isinstance(entry_count, int) or isinstance(entry_count, bool) or not 1 <= entry_count <= 1000:
        raise ValueError("invalid entry count")
    signer_role = checkpoint["signer_role"]
    if not isinstance(signer_role, str) or not 3 <= len(signer_role) <= 80:
        raise ValueError("invalid signer role")
    key_id = checkpoint["key_id"]
    if not isinstance(key_id, str) or not KEY_ID.fullmatch(key_id):
        raise ValueError("invalid key identifier")
    if checkpoint["signature_algorithm"] not in ALGORITHMS:
        raise ValueError("unsupported signature algorithm")

    issued = parse_time(checkpoint["issued_at"])
    current = now or datetime.now(timezone.utc)
    if issued > current:
        raise ValueError("checkpoint issued in the future")

    path = safe_file(root, checkpoint["ledger_path"])
    if hashlib.sha256(path.read_bytes()).hexdigest() != ledger_sha:
        raise ValueError("ledger file digest mismatch")
    try:
        ledger = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("malformed source ledger") from exc
    if not isinstance(ledger, dict):
        raise ValueError("malformed source ledger")
    for name, expected in (
        ("candidate_sha", candidate),
        ("decision", "NO-GO"),
        ("ledger_state", "VALID-NO-GO"),
    ):
        if ledger.get(name) != expected:
            raise ValueError(f"{name} drift")
    entries = ledger.get("entries")
    if not isinstance(entries, list) or len(entries) != entry_count:
        raise ValueError("entry count drift")
    last = entries[-1] if entries else None
    if not isinstance(last, dict) or last.get("entry_digest") != terminal:
        raise ValueError("terminal entry digest drift")
    source_digest = ledger.get("ledger_digest")
    if source_digest is not None and source_digest != ledger_digest:
        raise ValueError("ledger digest drift")

    material = {key: checkpoint[key] for key in sorted(TOP)}
    checkpoint_digest = canonical_digest(material)
    return {
        "schema": "lionsforge.public-operations-freshness-ledger-checkpoint-report",
        "schema_version": 1,
        "candidate_sha": candidate,
        "decision": "NO-GO",
        "checkpoint_state": "VALID-NO-GO",
        "checkpoint_sequence": sequence,
        "entry_count": entry_count,
        "terminal_entry_digest": terminal,
        "key_id": key_id,
        "checkpoint_digest": checkpoint_digest,
        "authorization": "NONE",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint")
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--expected-candidate")
    parser.add_argument("--minimum-sequence", type=int)
    parser.add_argument("--expected-previous")
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        checkpoint = json.loads(Path(args.checkpoint).read_text(encoding="utf-8"))
        if not isinstance(checkpoint, dict):
            raise ValueError("checkpoint must be an object")
        report = validate(
            checkpoint,
            Path(args.repository_root),
            args.expected_candidate,
            args.minimum_sequence,
            args.expected_previous,
        )
        raw = json.dumps(report, sort_keys=True, indent=2) + "\n"
        if args.output:
            Path(args.output).write_text(raw, encoding="utf-8")
        else:
            print(raw, end="")
        return 0
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"checkpoint validation failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
