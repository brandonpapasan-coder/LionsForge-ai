#!/usr/bin/env python3
"""Validate one signed checkpoint for an append-only public-operations witness ledger."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
IDENT = re.compile(r"^[a-z0-9][a-z0-9._-]{7,127}$")
SAFE_PATH = re.compile(r"^[A-Za-z0-9._/-]+$")
ZERO = "0" * 64
MAX_VALIDITY = timedelta(days=30)
ALGORITHMS = {"ed25519-sha256", "ecdsa-p256-sha256"}
TOP = {
    "schema", "schema_version", "candidate_sha", "decision", "checkpoint_state",
    "witness_ledger_path", "witness_ledger_sha256", "witness_ledger_digest",
    "entry_count", "terminal_entry_digest", "checkpoint_sequence",
    "previous_checkpoint_digest", "signer_role", "signer_key_id",
    "signature_algorithm", "signature_sha256", "nonce_sha256", "issued_at", "expires_at",
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


def safe_file(root: Path, relative: object) -> Path:
    if not isinstance(relative, str) or not SAFE_PATH.fullmatch(relative):
        raise ValueError("unsafe witness ledger path")
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("unsafe witness ledger path")
    path = root / candidate
    if path.is_symlink() or not path.is_file():
        raise ValueError("witness ledger path must be a regular file")
    resolved_root = root.resolve()
    resolved = path.resolve()
    if resolved_root not in resolved.parents:
        raise ValueError("witness ledger path escapes repository root")
    return path


def reject_secret_keys(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).lower()
            if any(marker in normalized for marker in FORBIDDEN):
                raise ValueError("secret-like key is forbidden")
            reject_secret_keys(item)
    elif isinstance(value, list):
        for item in value:
            reject_secret_keys(item)


def validate(
    checkpoint: object,
    repository_root: Path,
    expected_candidate: str | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    if not isinstance(checkpoint, dict) or set(checkpoint) != TOP:
        raise ValueError("checkpoint keys do not match contract")
    reject_secret_keys(checkpoint)
    if checkpoint["schema"] != "lionsforge.public-operations.witness-ledger-checkpoint" or checkpoint["schema_version"] != 1:
        raise ValueError("unsupported checkpoint schema")
    candidate = checkpoint["candidate_sha"]
    if not isinstance(candidate, str) or not SHA40.fullmatch(candidate):
        raise ValueError("invalid candidate_sha")
    if expected_candidate is not None and candidate != expected_candidate:
        raise ValueError("candidate drift")
    if checkpoint["decision"] != "NO-GO" or checkpoint["checkpoint_state"] != "VALID-NO-GO":
        raise ValueError("checkpoint must preserve NO-GO")

    path = safe_file(repository_root, checkpoint["witness_ledger_path"])
    raw = path.read_bytes()
    source_sha = hashlib.sha256(raw).hexdigest()
    if source_sha != require_digest(checkpoint["witness_ledger_sha256"], "witness_ledger_sha256"):
        raise ValueError("witness ledger byte drift")
    try:
        ledger = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("malformed witness ledger JSON") from exc
    reject_secret_keys(ledger)
    if not isinstance(ledger, dict):
        raise ValueError("witness ledger must be an object")
    if ledger.get("schema") != "lionsforge.public-operations-checkpoint-ledger-witness-ledger":
        raise ValueError("unexpected witness ledger schema")
    if ledger.get("schema_version") != 1:
        raise ValueError("unexpected witness ledger schema version")
    if ledger.get("candidate_sha") != candidate:
        raise ValueError("witness ledger candidate drift")
    if ledger.get("decision") != "NO-GO" or ledger.get("ledger_state") != "VALID-NO-GO":
        raise ValueError("witness ledger state drift")
    entries = ledger.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("witness ledger entries must be non-empty")
    ledger_digest = canonical_digest(ledger)
    if ledger_digest != require_digest(checkpoint["witness_ledger_digest"], "witness_ledger_digest"):
        raise ValueError("witness ledger digest drift")
    if checkpoint["entry_count"] != len(entries):
        raise ValueError("witness ledger entry count drift")
    terminal = entries[-1].get("entry_digest") if isinstance(entries[-1], dict) else None
    if terminal != require_digest(checkpoint["terminal_entry_digest"], "terminal_entry_digest"):
        raise ValueError("terminal entry digest drift")

    sequence = checkpoint["checkpoint_sequence"]
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        raise ValueError("invalid checkpoint sequence")
    previous = require_digest(checkpoint["previous_checkpoint_digest"], "previous_checkpoint_digest", allow_zero=True)
    if sequence == 1 and previous != ZERO:
        raise ValueError("first checkpoint must use zero previous digest")
    if sequence > 1 and previous == ZERO:
        raise ValueError("later checkpoint requires previous digest")
    if checkpoint["signer_role"] != "independent-witness-ledger-checkpoint-signer":
        raise ValueError("invalid signer role")
    for name in ("signer_key_id",):
        value = checkpoint[name]
        if not isinstance(value, str) or not IDENT.fullmatch(value):
            raise ValueError(f"invalid {name}")
    if checkpoint["signature_algorithm"] not in ALGORITHMS:
        raise ValueError("unsupported signature algorithm")
    signature = require_digest(checkpoint["signature_sha256"], "signature_sha256")
    nonce = require_digest(checkpoint["nonce_sha256"], "nonce_sha256")
    identities = [ledger_digest, terminal, signature, nonce]
    if previous != ZERO:
        identities.append(previous)
    if len(set(identities)) != len(identities):
        raise ValueError("duplicate identity material")

    issued = parse_time(checkpoint["issued_at"], "issued_at")
    expires = parse_time(checkpoint["expires_at"], "expires_at")
    current = now or datetime.now(timezone.utc)
    if issued > current:
        raise ValueError("future checkpoint issuance")
    if expires <= issued:
        raise ValueError("invalid checkpoint expiry ordering")
    if expires - issued > MAX_VALIDITY:
        raise ValueError("excessive checkpoint validity")
    if expires <= current:
        raise ValueError("expired checkpoint")

    material = {key: checkpoint[key] for key in sorted(TOP)}
    checkpoint_digest = canonical_digest(material)
    return {
        "schema": "lionsforge.public-operations.witness-ledger-checkpoint-report",
        "schema_version": 1,
        "candidate_sha": candidate,
        "decision": "NO-GO",
        "checkpoint_state": "VALID-NO-GO",
        "authorization": "NONE",
        "entry_count": len(entries),
        "terminal_entry_digest": terminal,
        "checkpoint_sequence": sequence,
        "checkpoint_digest": checkpoint_digest,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint")
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--expected-candidate")
    parser.add_argument("--output")
    args = parser.parse_args()
    checkpoint = json.loads(Path(args.checkpoint).read_text(encoding="utf-8"))
    result = validate(checkpoint, Path(args.repository_root), args.expected_candidate)
    rendered = json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
