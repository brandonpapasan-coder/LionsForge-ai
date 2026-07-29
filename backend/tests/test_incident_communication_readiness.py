from __future__ import annotations

import copy
import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_incident_communication_readiness.py"
EXAMPLE = ROOT / "docs" / "incident-communication-readiness.example.json"
SPEC = spec_from_file_location("validate_incident_communication_readiness", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def example() -> dict[str, object]:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def test_example_is_complete_no_go() -> None:
    assert MODULE.validate_record(example(), "0" * 40) == {
        "candidate_sha": "0" * 40,
        "incident_class_count": 5,
        "decision": "NO-GO",
        "result": "VALID",
    }


def test_rejects_missing_duplicate_and_candidate_mismatch() -> None:
    value = example()
    value["incident_classes"] = value["incident_classes"][:-1]
    with pytest.raises(ValueError, match="required incident classes are missing"):
        MODULE.validate_record(value)

    value = example()
    value["incident_classes"].append(copy.deepcopy(value["incident_classes"][0]))
    with pytest.raises(ValueError, match="duplicate incident class id"):
        MODULE.validate_record(value)

    with pytest.raises(ValueError, match="does not match expected candidate"):
        MODULE.validate_record(example(), "a" * 40)


def test_rejects_secret_keys_and_invalid_timing() -> None:
    value = example()
    value["api_key"] = "example"
    with pytest.raises(ValueError, match="top-level keys"):
        MODULE.validate_record(value)

    value = example()
    value["incident_classes"][0]["initial_update_target_minutes"] = 120
    with pytest.raises(ValueError, match="cannot exceed recurring cadence"):
        MODULE.validate_record(value)


def test_go_requires_every_incident_class_verified() -> None:
    value = example()
    value["decision"] = "GO"
    with pytest.raises(ValueError, match="GO requires every incident class"):
        MODULE.validate_record(value)
