from __future__ import annotations

import sys
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_internal_alpha_defect_lifecycle.py"
SPEC = spec_from_file_location("validate_internal_alpha_defect_lifecycle", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

NOW = datetime(2026, 7, 31, 14, tzinfo=timezone.utc)
CANDIDATE = "a" * 40


def build() -> dict[str, object]:
    return {
        "schema": "lionsforge.internal-alpha.defect-lifecycle",
        "schema_version": 1,
        "candidate_sha": CANDIDATE,
        "authorization": "INTERNAL-ALPHA-ONLY",
        "environment": "isolated-internal-alpha",
        "defects": [{
            "defect_id": "defect_0001",
            "feedback_id": "feedback_0001",
            "tester_id": "tester_0001",
            "session_id": "session_0001",
            "release_candidate": "rc_build-0001",
            "severity": "high",
            "previous_severity": "high",
            "state": "verified",
            "previous_state": "fixed",
            "regression": "none",
            "owner_ref": "operator_001",
            "reason_codes": ["fix-validated"],
            "created_at": "2026-07-31T10:00:00Z",
            "updated_at": "2026-07-31T13:00:00Z",
            "verified_at": "2026-07-31T13:00:00Z",
        }],
    }


def validate(value: object) -> dict[str, object]:
    return MODULE.validate(value, CANDIDATE, now=NOW)


def test_valid_manifest_is_deterministic() -> None:
    assert validate(build()) == validate(build())
    report = validate(build())
    assert report["authorization"] == "INTERNAL-ALPHA-ONLY"
    assert report["defect_count"] == 1
    assert len(report["report_digest"]) == 64


def test_rejects_candidate_environment_and_authorization_drift() -> None:
    value = build(); value["candidate_sha"] = "b" * 40
    with pytest.raises(ValueError, match="candidate mismatch"): validate(value)
    value = build(); value["environment"] = "production"
    with pytest.raises(ValueError, match="isolated-internal-alpha"): validate(value)
    value = build(); value["authorization"] = "PUBLIC-BETA"
    with pytest.raises(ValueError, match="INTERNAL-ALPHA-ONLY"): validate(value)


def test_rejects_transition_and_unverified_closure() -> None:
    value = build(); value["defects"][0]["state"] = "accepted"; value["defects"][0]["previous_state"] = "fixed"; value["defects"][0]["verified_at"] = None
    with pytest.raises(ValueError, match="transition regression"): validate(value)
    value = build(); value["defects"][0]["state"] = "closed"; value["defects"][0]["verified_at"] = None
    with pytest.raises(ValueError, match="verified_at is required"): validate(value)


def test_rejects_unapproved_downgrade_and_sensitive_fields() -> None:
    value = build(); value["defects"][0]["severity"] = "medium"
    with pytest.raises(ValueError, match="downgrade requires approval"): validate(value)
    value = build(); value["defects"][0]["comment"] = "free form"
    with pytest.raises(ValueError, match="free-form key"): validate(value)
