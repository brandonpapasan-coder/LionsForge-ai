from __future__ import annotations

import sys
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_internal_alpha_session_assignment.py"
SPEC = spec_from_file_location("validate_internal_alpha_session_assignment", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

NOW = datetime(2026, 7, 30, 18, tzinfo=timezone.utc)
CANDIDATE = "a" * 40


def build() -> dict[str, object]:
    return {
        "schema": "lionsforge.internal-alpha.session-assignment",
        "schema_version": 1,
        "candidate_sha": CANDIDATE,
        "authorization": "INTERNAL-ALPHA-ONLY",
        "environment": "isolated-internal-alpha",
        "sessions": [{
            "session_id": "session_0001",
            "tester_id": "tester_0001",
            "release_candidate": "rc_build-0001",
            "purpose": "validation",
            "approver_ref": "operator_001",
            "issued_at": "2026-07-30T17:00:00Z",
            "starts_at": "2026-07-30T18:00:00Z",
            "ends_at": "2026-07-30T20:00:00Z",
        }],
    }


def validate(value: object) -> dict[str, object]:
    return MODULE.validate(value, CANDIDATE, now=NOW)


def test_valid_manifest_is_deterministic_and_internal_only() -> None:
    first = validate(build())
    second = validate(build())
    assert first == second
    assert first["authorization"] == "INTERNAL-ALPHA-ONLY"
    assert first["session_count"] == 1
    assert len(first["report_digest"]) == 64


def test_rejects_candidate_environment_and_authorization_drift() -> None:
    value = build(); value["candidate_sha"] = "b" * 40
    with pytest.raises(ValueError, match="candidate mismatch"): validate(value)
    value = build(); value["environment"] = "production"
    with pytest.raises(ValueError, match="isolated-internal-alpha"): validate(value)
    value = build(); value["authorization"] = "PUBLIC-BETA"
    with pytest.raises(ValueError, match="INTERNAL-ALPHA-ONLY"): validate(value)


def test_rejects_duplicate_privileged_and_long_sessions() -> None:
    value = build(); value["sessions"].append(dict(value["sessions"][0]))
    with pytest.raises(ValueError, match="duplicate session_id"): validate(value)
    value = build(); value["sessions"][0]["purpose"] = "admin"
    with pytest.raises(ValueError, match="least privilege"): validate(value)
    value = build(); value["sessions"][0]["ends_at"] = "2026-07-31T10:00:00Z"
    with pytest.raises(ValueError, match="at most 12 hours"): validate(value)


def test_rejects_overlap_sensitive_fields_and_expiration() -> None:
    value = build()
    second = dict(value["sessions"][0])
    second.update({"session_id": "session_0002", "release_candidate": "rc_build-0002"})
    value["sessions"].append(second)
    with pytest.raises(ValueError, match="overlapping tester sessions"): validate(value)
    value = build(); value["sessions"][0]["email"] = "person@example.com"
    with pytest.raises(ValueError, match="personal or secret-like"): validate(value)
    value = build(); value["sessions"][0]["ends_at"] = "2026-07-30T17:30:00Z"
    with pytest.raises(ValueError, match="expired session"): validate(value)
