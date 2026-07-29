from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_public_operations_evidence_freshness.py"
SPEC = spec_from_file_location("validate_public_operations_evidence_freshness", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def write_json(path: Path, value: object) -> str:
    raw = json.dumps(value, sort_keys=True).encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def build(tmp_path: Path) -> dict[str, object]:
    candidate = "0" * 40
    reconciliation = {"candidate_sha": candidate, "decision": "NO-GO"}
    digest = write_json(tmp_path / "reconciliation.json", reconciliation)
    return {
        "schema": "lionsforge.public-operations-evidence-freshness",
        "schema_version": 1,
        "candidate_sha": candidate,
        "decision": "NO-GO",
        "reconciliation_path": "reconciliation.json",
        "reconciliation_sha256": digest,
        "generated_at": "2026-07-29T12:00:00Z",
        "valid_until": "2026-07-30T12:00:00Z",
        "maximum_validity_hours": 24,
        "owner_role": "evidence-owner",
        "reviewer_role": "independent-reviewer",
    }


def test_valid_no_go_record(tmp_path: Path) -> None:
    result = MODULE.validate(
        build(tmp_path),
        tmp_path,
        "0" * 40,
        datetime(2026, 7, 29, 18, tzinfo=timezone.utc),
    )
    assert result["freshness_state"] == "VALID-NO-GO"
    assert len(result["freshness_digest"]) == 64


def test_rejects_expired_or_excessive_window(tmp_path: Path) -> None:
    record = build(tmp_path)
    with pytest.raises(ValueError, match="expired"):
        MODULE.validate(record, tmp_path, now=datetime(2026, 7, 31, tzinfo=timezone.utc))
    record = build(tmp_path)
    record["maximum_validity_hours"] = 12
    with pytest.raises(ValueError, match="exceeds maximum"):
        MODULE.validate(record, tmp_path, now=datetime(2026, 7, 29, tzinfo=timezone.utc))


def test_rejects_role_overlap_and_candidate_drift(tmp_path: Path) -> None:
    record = build(tmp_path)
    record["reviewer_role"] = "Evidence-Owner"
    with pytest.raises(ValueError, match="roles must be separated"):
        MODULE.validate(record, tmp_path, now=datetime(2026, 7, 29, tzinfo=timezone.utc))
    record = build(tmp_path)
    with pytest.raises(ValueError, match="expected candidate"):
        MODULE.validate(record, tmp_path, "a" * 40, datetime(2026, 7, 29, tzinfo=timezone.utc))


def test_rejects_digest_and_unknown_keys(tmp_path: Path) -> None:
    record = build(tmp_path)
    record["reconciliation_sha256"] = "a" * 64
    with pytest.raises(ValueError, match="digest mismatch"):
        MODULE.validate(record, tmp_path, now=datetime(2026, 7, 29, tzinfo=timezone.utc))
    record = build(tmp_path)
    record["api_token"] = "forbidden"
    with pytest.raises(ValueError, match="top-level keys"):
        MODULE.validate(record, tmp_path, now=datetime(2026, 7, 29, tzinfo=timezone.utc))
