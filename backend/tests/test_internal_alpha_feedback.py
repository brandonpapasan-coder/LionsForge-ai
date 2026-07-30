from __future__ import annotations

import sys
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_internal_alpha_feedback.py"
SPEC = spec_from_file_location("validate_internal_alpha_feedback", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

NOW = datetime(2026, 7, 30, 18, tzinfo=timezone.utc)
CANDIDATE = "a" * 40


def build() -> dict[str, object]:
    return {
        "schema": "lionsforge.internal-alpha.feedback",
        "schema_version": 1,
        "candidate_sha": CANDIDATE,
        "authorization": "INTERNAL-ALPHA-ONLY",
        "environment": "isolated-internal-alpha",
        "feedback": [{
            "feedback_id": "feedback_0001",
            "tester_id": "tester_0001",
            "session_id": "session_0001",
            "release_candidate": "rc_build-0001",
            "category": "defect",
            "severity": "high",
            "reproducibility": "always",
            "component_code": "research.workspace",
            "reason_codes": ["incorrect-output"],
            "observed_at": "2026-07-30T17:30:00Z",
            "session_starts_at": "2026-07-30T17:00:00Z",
            "session_ends_at": "2026-07-30T18:00:00Z",
        }],
    }


def validate(value: object) -> dict[str, object]:
    return MODULE.validate(value, CANDIDATE, now=NOW)


def test_valid_manifest_is_deterministic_and_internal_only() -> None:
    assert validate(build()) == validate(build())
    report = validate(build())
    assert report["authorization"] == "INTERNAL-ALPHA-ONLY"
    assert report["feedback_count"] == 1
    assert len(report["report_digest"]) == 64


def test_rejects_candidate_environment_and_authorization_drift() -> None:
    value = build(); value["candidate_sha"] = "b" * 40
    with pytest.raises(ValueError, match="candidate mismatch"): validate(value)
    value = build(); value["environment"] = "production"
    with pytest.raises(ValueError, match="isolated-internal-alpha"): validate(value)
    value = build(); value["authorization"] = "PUBLIC-BETA"
    with pytest.raises(ValueError, match="INTERNAL-ALPHA-ONLY"): validate(value)


def test_rejects_duplicate_sensitive_and_invalid_feedback() -> None:
    value = build(); value["feedback"].append(dict(value["feedback"][0]))
    with pytest.raises(ValueError, match="duplicate feedback_id"): validate(value)
    value = build(); value["feedback"][0]["comment"] = "free form"
    with pytest.raises(ValueError, match="free-form key"): validate(value)
    value = build(); value["feedback"][0]["category"] = "usability"; value["feedback"][0]["severity"] = "critical"
    with pytest.raises(ValueError, match="reserved for defects"): validate(value)


def test_rejects_future_and_out_of_session_observations() -> None:
    value = build(); value["feedback"][0]["observed_at"] = "2026-07-30T19:00:00Z"
    with pytest.raises(ValueError, match="future observation"): validate(value)
    value = build(); value["feedback"][0]["observed_at"] = "2026-07-30T16:30:00Z"
    with pytest.raises(ValueError, match="outside session window"): validate(value)
