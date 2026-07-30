#!/usr/bin/env python3
"""Validate one independent witness receipt for a public-operations checkpoint ledger."""
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
    "schema", "schema_version", "candidate_sha", "decision", "witness_state",
    "checkpoint_ledger_path", "checkpoint_ledger_sha256", "checkpoint_ledger_digest",
    "entry_count", "terminal_entry_digest", "witness_receipt_id", "witness_role",
    "witness_key_id", "signature_algorithm", "signature_sha256", "nonce_sha256",
    "issued_at", "expires_at",
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


def require_digest(value: object, name: str) -> str:
    if not isinstance(value, str) or not SHA256.fullmatch(value) or value == ZERO:
        raise ValueError(f"invalid {name}")
    return value


def safe_file(root: Path, relative: object) -> Path:
    if not isinstance(relative, str) or not SAFE_PATH.fullmatch(relative):
        raise ValueError("unsafe checkpoint ledger path")
    if relative.startswith("/") or ".." in Path(relative).parts:
        raise ValueError("unsafe checkpoint ledger path")
    path = root / relative
    resolved_root = root.resolve()
    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ValueError("checkpoint ledger file missing") from exc
    if path.is_symlink() or resolved_root not in resolved.parents:
        raise ValueError("unsafe checkpoint ledger path")
    return resolved


def validate(value: object, repository_root: Path, expected_candidate: str | None = None,
             *, now: datetime | None = None) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != TOP:
        raise ValueError("invalid top-level keys")
    lowered = json.dumps(value, sort_keys=True).lower()
    if any(term in lowered for term in FORBIDDEN):
        raise ValueError("secret-like key or value")
    if value["schema"] != "lionsforge.public-operations-checkpoint-ledger-witness" or value["schema_version"] != 1:
        raise ValueError("unsupported witness schema")
    candidate = value["candidate_sha"]
    if not isinstance(candidate, str) or not SHA40.fullmatch(candidate):
        raise ValueError("invalid candidate_sha")
    if expected_candidate is not None and candidate != expected_candidate:
        raise ValueError("candidate drift")
    if value["decision"] != "NO-GO" or value["witness_state"] != "VALID-NO-GO":
        raise ValueError("witness must preserve NO-GO")

    ledger_path = safe_file(repository_root, value["checkpoint_ledger_path"])
    raw = ledger_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != require_digest(value["checkpoint_ledger_sha256"], "checkpoint_ledger_sha256"):
        raise ValueError("checkpoint ledger byte drift")
    try:
        ledger = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("malformed checkpoint ledger JSON") from exc
    if not isinstance(ledger, dict):
        raise ValueError("malformed checkpoint ledger")
    for key in ledger:
        if any(term in str(key).lower() for term in FORBIDDEN):
            raise ValueError("secret-like checkpoint ledger key")
    if ledger.get("candidate_sha") != candidate:
        raise ValueError("checkpoint ledger candidate drift")
    if ledger.get("decision") != "NO-GO" or ledger.get("ledger_state") != "VALID-NO-GO":
        raise ValueError("checkpoint ledger state drift")
    entries = ledger.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("checkpoint ledger entries missing")
    ledger_digest = require_digest(value["checkpoint_ledger_digest"], "checkpoint_ledger_digest")
    source_digest = ledger.get("checkpoint_ledger_digest") or canonical_digest(ledger)
    if source_digest != ledger_digest:
        raise ValueError("checkpoint ledger digest drift")
    if value["entry_count"] != len(entries) or not isinstance(value["entry_count"], int) or value["entry_count"] < 1:
        raise ValueError("entry count drift")
    terminal = entries[-1].get("entry_digest") if isinstance(entries[-1], dict) else None
    if require_digest(value["terminal_entry_digest"], "terminal_entry_digest") != terminal:
        raise ValueError("terminal entry digest drift")

    receipt_id = value["witness_receipt_id"]
    role = value["witness_role"]
    key_id = value["witness_key_id"]
    if not isinstance(receipt_id, str) or not IDENT.fullmatch(receipt_id):
        raise ValueError("invalid witness receipt ID")
    if role != "independent-checkpoint-ledger-witness":
        raise ValueError("invalid witness role")
    if not isinstance(key_id, str) or not IDENT.fullmatch(key_id):
        raise ValueError("invalid witness key ID")
    if value["signature_algorithm"] not in ALGORITHMS:
        raise ValueError("unsupported signature algorithm")
    signature = require_digest(value["signature_sha256"], "signature_sha256")
    nonce = require_digest(value["nonce_sha256"], "nonce_sha256")
    if len({ledger_digest, value["terminal_entry_digest"], signature, nonce}) != 4:
        raise ValueError("duplicate identity material")

    issued = parse_time(value["issued_at"], "issued_at")
    expires = parse_time(value["expires_at"], "expires_at")
    current = now or datetime.now(timezone.utc)
    if issued > current:
        raise ValueError("future witness issuance")
    if expires <= issued:
        raise ValueError("invalid witness expiry ordering")
    if expires - issued > MAX_VALIDITY:
        raise ValueError("excessive witness validity window")
    if current >= expires:
        raise ValueError("expired witness receipt")

    material = {key: value[key] for key in sorted(TOP)}
    return {
        "schema": "lionsforge.public-operations-checkpoint-ledger-witness-report",
        "schema_version": 1,
        "candidate_sha": candidate,
        "decision": "NO-GO",
        "witness_state": "VALID-NO-GO",
        "authorization": "NONE",
        "witness_receipt_id": receipt_id,
        "checkpoint_ledger_digest": ledger_digest,
        "witness_digest": canonical_digest(material),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    parser.add_argument("--expected-candidate")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    value = json.loads(args.receipt.read_text(encoding="utf-8"))
    report = validate(value, args.repository_root, args.expected_candidate)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
