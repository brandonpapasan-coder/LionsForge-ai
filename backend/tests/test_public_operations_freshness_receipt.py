from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_public_operations_freshness_receipt.py"
SPEC = spec_from_file_location("validate_public_operations_freshness_receipt", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def write_json(path: Path, value: object) -> str:
    raw = json.dumps(value, sort_keys=True).encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def build(tmp_path: Path) -> dict[str, object]:
    candidate = "a" * 40
    freshness_digest = "b" * 64
    report = {
        "candidate_sha": candidate,
        "decision": "NO-GO",
        "freshness_state": "VALID-NO-GO",
        "freshness_digest": freshness_digest,
    }
    report_digest = write_json(tmp_path / "freshness-report.json", report)
    return {
        "schema": "lionsforge.public-operations-freshness-receipt",
        "schema_version": 1,
        "candidate_sha": candidate,
        "decision": "NO-GO",
        "freshness_state": "VALID-NO-GO",
        "freshness_report_path": "freshness-report.json",
        "freshness_report_sha256": report_digest,
        "freshness_digest": freshness_digest,
        "receipt_id": "freshness-receipt-0001",
        "nonce_sha256": "c" * 64,
        "issued_at": "2026-07-29T12:00:00Z",
    }


def test_valid_receipt_is_non_authorizing(tmp_path: Path) -> None:
    result = MODULE.validate(
        build(tmp_path),
        tmp_path,
        "a" * 40,
        datetime(2026, 7, 29, 13, tzinfo=timezone.utc),
    )
    assert result["receipt_state"] == "VALID-NO-GO"
    assert result["decision"] == "NO-GO"
    assert len(result["receipt_digest"]) == 64


def test_rejects_candidate_and_source_digest_drift(tmp_path: Path) -> None:
    receipt = build(tmp_path)
    with pytest.raises(ValueError, match="expected candidate"):
        MODULE.validate(receipt, tmp_path, "d" * 40, datetime(2026, 7, 29, 13, tzinfo=timezone.utc))
    receipt = build(tmp_path)
    receipt["freshness_report_sha256"] = "d" * 64
    with pytest.raises(ValueError, match="digest mismatch"):
        MODULE.validate(receipt, tmp_path, now=datetime(2026, 7, 29, 13, tzinfo=timezone.utc))


def test_rejects_state_drift_and_future_issue_time(tmp_path: Path) -> None:
    receipt = build(tmp_path)
    report_path = tmp_path / "freshness-report.json"
    report = json.loads(report_path.read_text())
    report["freshness_state"] = "BLOCKED"
    receipt["freshness_report_sha256"] = write_json(report_path, report)
    with pytest.raises(ValueError, match="state drift"):
        MODULE.validate(receipt, tmp_path, now=datetime(2026, 7, 29, 13, tzinfo=timezone.utc))
    receipt = build(tmp_path)
    receipt["issued_at"] = "2026-07-30T00:00:00Z"
    with pytest.raises(ValueError, match="future"):
        MODULE.validate(receipt, tmp_path, now=datetime(2026, 7, 29, 13, tzinfo=timezone.utc))


def test_rejects_zero_or_duplicate_identity_digests_and_unknown_keys(tmp_path: Path) -> None:
    receipt = build(tmp_path)
    receipt["nonce_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="invalid nonce"):
        MODULE.validate(receipt, tmp_path, now=datetime(2026, 7, 29, 13, tzinfo=timezone.utc))
    receipt = build(tmp_path)
    receipt["nonce_sha256"] = receipt["freshness_digest"]
    with pytest.raises(ValueError, match="must be distinct"):
        MODULE.validate(receipt, tmp_path, now=datetime(2026, 7, 29, 13, tzinfo=timezone.utc))
    receipt = build(tmp_path)
    receipt["api_token"] = "forbidden"
    with pytest.raises(ValueError, match="top-level keys"):
        MODULE.validate(receipt, tmp_path, now=datetime(2026, 7, 29, 13, tzinfo=timezone.utc))
