from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_operational_readiness_snapshot_ledger.py"
SPEC = spec_from_file_location("validate_operational_readiness_snapshot_ledger", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

NOW = datetime(2026, 7, 30, 15, tzinfo=timezone.utc)
CANDIDATE = "a" * 40


def write_snapshot(tmp_path: Path) -> tuple[str, str]:
    snapshot = {
        "candidate_sha": CANDIDATE,
        "readiness_state": "VALID-NO-GO",
        "authorization": "NONE",
        "issued_at": "2026-07-30T14:00:00Z",
        "expires_at": "2026-08-06T14:00:00Z",
        "snapshot_digest": "b" * 64,
    }
    raw = json.dumps(snapshot, sort_keys=True).encode()
    (tmp_path / "snapshot.json").write_bytes(raw)
    return hashlib.sha256(raw).hexdigest(), MODULE.canonical_digest(snapshot)


def build(tmp_path: Path) -> dict[str, object]:
    source_sha, snapshot_digest = write_snapshot(tmp_path)
    entry = {
        "sequence": 1,
        "snapshot_path": "snapshot.json",
        "snapshot_sha256": source_sha,
        "snapshot_digest": snapshot_digest,
        "issued_at": "2026-07-30T14:00:00Z",
        "previous_entry_digest": "0" * 64,
    }
    entry["entry_digest"] = MODULE.canonical_digest(entry)
    return {
        "schema": "lionsforge.operational-readiness.snapshot-ledger",
        "schema_version": 1,
        "candidate_sha": CANDIDATE,
        "decision": "NO-GO",
        "ledger_state": "VALID-NO-GO",
        "entries": [entry],
    }


def validate(value: object, tmp_path: Path) -> dict[str, object]:
    return MODULE.validate(value, tmp_path, CANDIDATE, now=NOW)


def test_valid_ledger_is_deterministic_and_non_authorizing(tmp_path: Path) -> None:
    ledger = build(tmp_path)
    first = validate(ledger, tmp_path)
    second = validate(ledger, tmp_path)
    assert first == second
    assert first["ledger_state"] == "VALID-NO-GO"
    assert first["authorization"] == "NONE"
    assert first["entry_count"] == 1
    assert len(first["ledger_digest"]) == 64


def test_rejects_source_candidate_and_authorization_drift(tmp_path: Path) -> None:
    ledger = build(tmp_path)
    ledger["entries"][0]["snapshot_sha256"] = "e" * 64
    with pytest.raises(ValueError, match="snapshot byte drift"):
        validate(ledger, tmp_path)

    ledger = build(tmp_path)
    snapshot = json.loads((tmp_path / "snapshot.json").read_text())
    snapshot["authorization"] = "DEPLOY"
    raw = json.dumps(snapshot, sort_keys=True).encode()
    (tmp_path / "snapshot.json").write_bytes(raw)
    ledger["entries"][0]["snapshot_sha256"] = hashlib.sha256(raw).hexdigest()
    ledger["entries"][0]["snapshot_digest"] = MODULE.canonical_digest(snapshot)
    ledger["entries"][0]["entry_digest"] = MODULE.canonical_digest({k: v for k, v in ledger["entries"][0].items() if k != "entry_digest"})
    with pytest.raises(ValueError, match="authorization must be NONE"):
        validate(ledger, tmp_path)


def test_rejects_sequence_link_and_digest_drift(tmp_path: Path) -> None:
    ledger = build(tmp_path)
    ledger["entries"][0]["sequence"] = 2
    with pytest.raises(ValueError, match="sequence gap"):
        validate(ledger, tmp_path)

    ledger = build(tmp_path)
    ledger["entries"][0]["previous_entry_digest"] = "e" * 64
    with pytest.raises(ValueError, match="broken previous-entry link"):
        validate(ledger, tmp_path)

    ledger = build(tmp_path)
    ledger["entries"][0]["snapshot_digest"] = "e" * 64
    with pytest.raises(ValueError, match="snapshot digest drift"):
        validate(ledger, tmp_path)


def test_rejects_expired_and_unsafe_snapshots(tmp_path: Path) -> None:
    ledger = build(tmp_path)
    with pytest.raises(ValueError, match="expired snapshot"):
        MODULE.validate(ledger, tmp_path, CANDIDATE, now=datetime(2026, 8, 7, tzinfo=timezone.utc))

    ledger = build(tmp_path)
    ledger["entries"][0]["snapshot_path"] = "../snapshot.json"
    with pytest.raises(ValueError, match="unsafe snapshot path"):
        validate(ledger, tmp_path)
