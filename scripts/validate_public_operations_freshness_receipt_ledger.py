#!/usr/bin/env python3
"""Validate an append-only public-operations freshness receipt ledger."""
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
ZERO = "0" * 64
TOP = {"schema", "schema_version", "candidate_sha", "decision", "ledger_state", "entries"}
ENTRY = {"sequence", "receipt_path", "receipt_sha256", "receipt_id", "nonce_sha256", "receipt_digest", "issued_at", "previous_entry_digest", "entry_digest"}
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


def safe_file(root: Path, relative: object) -> Path:
    if not isinstance(relative, str) or not SAFE_PATH.fullmatch(relative):
        raise ValueError("unsafe receipt path")
    if relative.startswith("/") or ".." in Path(relative).parts:
        raise ValueError("unsafe receipt path")
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise ValueError("receipt file missing or symlinked")
    return path


def validate(ledger: dict[str, object], root: Path, expected_candidate: str | None = None) -> dict[str, object]:
    if set(ledger) != TOP:
        raise ValueError("invalid top-level keys")
    if any(term in str(key).lower() for key in ledger for term in FORBIDDEN):
        raise ValueError("secret-like key detected")
    if ledger["schema"] != "lionsforge.public-operations-freshness-receipt-ledger" or ledger["schema_version"] != 1:
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

    ids: set[str] = set()
    nonces: set[str] = set()
    receipts: set[str] = set()
    previous = ZERO
    prior_time: datetime | None = None

    for index, raw in enumerate(entries, start=1):
        if not isinstance(raw, dict) or set(raw) != ENTRY:
            raise ValueError("invalid entry keys")
        if any(term in str(key).lower() for key in raw for term in FORBIDDEN):
            raise ValueError("secret-like key detected")
        if raw["sequence"] != index:
            raise ValueError("ledger sequence gap")
        path = safe_file(root, raw["receipt_path"])
        source_sha = raw["receipt_sha256"]
        if not isinstance(source_sha, str) or not SHA256.fullmatch(source_sha) or source_sha == ZERO:
            raise ValueError("invalid receipt SHA-256")
        if hashlib.sha256(path.read_bytes()).hexdigest() != source_sha:
            raise ValueError("receipt file digest mismatch")
        try:
            source = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError("malformed source receipt") from exc
        if source.get("candidate_sha") != candidate or source.get("decision") != "NO-GO" or source.get("receipt_state") != "VALID-NO-GO":
            raise ValueError("receipt candidate or state drift")
        for field in ("nonce_sha256", "receipt_digest"):
            value = raw[field]
            if not isinstance(value, str) or not SHA256.fullmatch(value) or value == ZERO:
                raise ValueError(f"invalid {field}")
            if source.get(field) != value:
                raise ValueError(f"{field} drift")
        receipt_id = raw["receipt_id"]
        if not isinstance(receipt_id, str) or source.get("receipt_id") != receipt_id:
            raise ValueError("receipt ID drift")
        if receipt_id in ids or raw["nonce_sha256"] in nonces or raw["receipt_digest"] in receipts:
            raise ValueError("duplicate receipt identity material")
        ids.add(receipt_id); nonces.add(raw["nonce_sha256"]); receipts.add(raw["receipt_digest"])
        issued = parse_time(raw["issued_at"])
        if source.get("issued_at") != raw["issued_at"]:
            raise ValueError("issued_at drift")
        if prior_time and issued <= prior_time:
            raise ValueError("issued_at must increase monotonically")
        prior_time = issued
        if raw["previous_entry_digest"] != previous:
            raise ValueError("broken previous-entry link")
        material = {key: raw[key] for key in ENTRY - {"entry_digest"}}
        expected_entry = canonical_digest(material)
        if raw["entry_digest"] != expected_entry:
            raise ValueError("entry digest mismatch")
        previous = expected_entry

    report = {
        "schema": "lionsforge.public-operations-freshness-receipt-ledger-report",
        "schema_version": 1,
        "candidate_sha": candidate,
        "decision": "NO-GO",
        "ledger_state": "VALID-NO-GO",
        "entry_count": len(entries),
        "head_entry_digest": previous,
    }
    report["ledger_digest"] = canonical_digest(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ledger")
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--expected-candidate")
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        value = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
        report = validate(value, Path(args.repository_root), args.expected_candidate)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise SystemExit(f"BLOCKED: {exc}") from exc
    rendered = json.dumps(report, sort_keys=True, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
