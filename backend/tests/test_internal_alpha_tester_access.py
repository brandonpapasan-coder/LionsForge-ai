from __future__ import annotations

import sys
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_internal_alpha_tester_access.py"
SPEC = spec_from_file_location("validate_internal_alpha_tester_access", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

NOW = datetime(2026, 7, 30, 15, tzinfo=timezone.utc)
CANDIDATE = "a" * 40


def build() -> dict[str, object]:
    return {
        "schema": "lionsforge.internal-alpha.tester-access",
        "schema_version": 1,
        "candidate_sha": CANDIDATE,
        "authorization": "INTERNAL-ALPHA-ONLY",
        "environment": "isolated-internal-alpha",
        "testers": [{
            "tester_id": "tester_0001",
            "status": "approved",
            "role": "validator",
            "approver_ref": "operator_001",
            "issued_at": "2026-07-30T14:00:00Z",
            "expires_at": "2026-08-06T14:00:00Z",
        }],
    }


def validate(value: object) -> dict[str, object]:
    return MODULE.validate(value, CANDIDATE, now=NOW)


def test_valid_manifest_is_deterministic_and_internal_only() -> None:
    first = validate(build())
    second = validate(build())
    assert first == second
    assert first["authorization"] == "INTERNAL-ALPHA-ONLY"
    assert first["environment"] == "isolated-internal-alpha"
    assert first["tester_count"] == 1
    assert len(first["report_digest"]) == 64


def test_rejects_candidate_environment_and_authorization_drift() -> None:
    value = build()
    value["candidate_sha"] = "b" * 40
    with pytest.raises(ValueError, match="candidate mismatch"):
        validate(value)
    value = build()
    value["environment"] = "production"
    with pytest.raises(ValueError, match="isolated-internal-alpha"):
        validate(value)
    value = build()
    value["authorization"] = "PUBLIC-BETA"
    with pytest.raises(ValueError, match="INTERNAL-ALPHA-ONLY"):
        validate(value)


def test_rejects_duplicate_privileged_and_expired_access() -> None:
    value = build()
    value["testers"].append(dict(value["testers"][0]))
    with pytest.raises(ValueError, match="duplicate tester_id"):
        validate(value)
    value = build()
    value["testers"][0]["role"] = "admin"
    with pytest.raises(ValueError, match="least privilege"):
        validate(value)
    value = build()
    value["testers"][0]["expires_at"] = "2026-07-30T14:30:00Z"
    with pytest.raises(ValueError, match="expired access"):
        validate(value)


def test_rejects_personal_fields_and_excessive_duration() -> None:
    value = build()
    value["testers"][0]["email"] = "person@example.com"
    with pytest.raises(ValueError, match="personal or secret-like"):
        validate(value)
    value = build()
    value["testers"][0]["expires_at"] = "2026-09-30T14:00:00Z"
    with pytest.raises(ValueError, match="at most 30 days"):
        validate(value)
