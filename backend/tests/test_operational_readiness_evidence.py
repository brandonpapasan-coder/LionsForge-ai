from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_operational_readiness_evidence.py"
SPEC = spec_from_file_location("validate_operational_readiness_evidence", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

NOW = datetime(2026, 7, 30, 14, tzinfo=timezone.utc)
CANDIDATE = "a" * 40


def write_report(tmp_path: Path, name: str = "checkpoint.json") -> tuple[str, str]:
    report = {
        "candidate_sha": CANDIDATE,
        "ledger_state": "VALID-NO-GO",
        "authorization": "NONE",
        "issued_at": "2026-07-30T13:00:00Z",
        "expires_at": "2026-08-06T13:00:00Z",
    }
    raw = json.dumps(report, sort_keys=True).encode()
    (tmp_path / name).write_bytes(raw)
    return hashlib.sha256(raw).hexdigest(), MODULE.canonical_digest(report)


def build(tmp_path: Path) -> dict[str, object]:
    report_sha, report_digest = write_report(tmp_path)
    return {
        "schema": "lionsforge.operational-readiness.evidence-manifest",
        "schema_version": 1,
        "candidate_sha": CANDIDATE,
        "decision": "NO-GO",
        "readiness_state": "VALID-NO-GO",
        "evidence": [{
            "evidence_type": "witness-checkpoint-ledger",
            "report_path": "checkpoint.json",
            "report_sha256": report_sha,
            "report_digest": report_digest,
            "issued_at": "2026-07-30T13:00:00Z",
            "expires_at": "2026-08-06T13:00:00Z",
        }],
    }


def validate(value: object, tmp_path: Path) -> dict[str, object]:
    return MODULE.validate(value, tmp_path, CANDIDATE, now=NOW)


def test_valid_manifest_emits_deterministic_non_authorizing_snapshot(tmp_path: Path) -> None:
    manifest = build(tmp_path)
    first = validate(manifest, tmp_path)
    second = validate(manifest, tmp_path)
    assert first == second
    assert first["readiness_state"] == "VALID-NO-GO"
    assert first["authorization"] == "NONE"
    assert first["evidence_count"] == 1
    assert len(first["snapshot_digest"]) == 64


def test_rejects_candidate_state_and_authorization_drift(tmp_path: Path) -> None:
    manifest = build(tmp_path)
    manifest["candidate_sha"] = "b" * 40
    with pytest.raises(ValueError, match="candidate mismatch"):
        validate(manifest, tmp_path)

    manifest = build(tmp_path)
    report = json.loads((tmp_path / "checkpoint.json").read_text())
    report["ledger_state"] = "VALID-GO"
    (tmp_path / "checkpoint.json").write_text(json.dumps(report, sort_keys=True))
    with pytest.raises(ValueError, match="byte drift"):
        validate(manifest, tmp_path)

    manifest = build(tmp_path)
    report = json.loads((tmp_path / "checkpoint.json").read_text())
    report["authorization"] = "DEPLOY"
    raw = json.dumps(report, sort_keys=True).encode()
    (tmp_path / "checkpoint.json").write_bytes(raw)
    manifest["evidence"][0]["report_sha256"] = hashlib.sha256(raw).hexdigest()
    manifest["evidence"][0]["report_digest"] = MODULE.canonical_digest(report)
    with pytest.raises(ValueError, match="authorization must be NONE"):
        validate(manifest, tmp_path)


def test_rejects_expired_duplicate_and_unsafe_evidence(tmp_path: Path) -> None:
    manifest = build(tmp_path)
    manifest["evidence"][0]["expires_at"] = "2026-07-30T13:30:00Z"
    with pytest.raises(ValueError, match="expired evidence"):
        validate(manifest, tmp_path)

    manifest = build(tmp_path)
    manifest["evidence"].append(dict(manifest["evidence"][0]))
    with pytest.raises(ValueError, match="duplicate evidence identity"):
        validate(manifest, tmp_path)

    manifest = build(tmp_path)
    manifest["evidence"][0]["report_path"] = "../checkpoint.json"
    with pytest.raises(ValueError, match="unsafe report path"):
        validate(manifest, tmp_path)


def test_rejects_report_digest_and_time_drift(tmp_path: Path) -> None:
    manifest = build(tmp_path)
    manifest["evidence"][0]["report_digest"] = "e" * 64
    with pytest.raises(ValueError, match="report digest drift"):
        validate(manifest, tmp_path)

    manifest = build(tmp_path)
    manifest["evidence"][0]["issued_at"] = "2026-07-30T12:00:00Z"
    with pytest.raises(ValueError, match="issue-time drift"):
        validate(manifest, tmp_path)
