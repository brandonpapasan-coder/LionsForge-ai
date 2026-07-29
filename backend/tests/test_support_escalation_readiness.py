from __future__ import annotations
import copy, json, sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_support_escalation_readiness.py"
EXAMPLE = ROOT / "docs" / "support-escalation-readiness.example.json"
SPEC = spec_from_file_location("validate_support_escalation_readiness", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

def example(): return json.loads(EXAMPLE.read_text(encoding="utf-8"))

def test_example_is_complete_no_go() -> None:
    assert MODULE.validate_record(example(), "0" * 40) == {
        "candidate_sha": "0" * 40,
        "channel_count": 4,
        "decision": "NO-GO",
        "result": "VALID",
    }

def test_rejects_missing_duplicate_and_candidate_mismatch() -> None:
    value = example(); value["channels"] = value["channels"][:-1]
    with pytest.raises(ValueError, match="required channels are missing"): MODULE.validate_record(value)
    value = example(); value["channels"].append(copy.deepcopy(value["channels"][0]))
    with pytest.raises(ValueError, match="duplicate channel id"): MODULE.validate_record(value)
    with pytest.raises(ValueError, match="does not match expected candidate"): MODULE.validate_record(example(), "a" * 40)

def test_rejects_personal_address_secrets_and_invalid_targets() -> None:
    value = example(); value["channels"][0]["public_contact"] = "person@gmail.com"
    with pytest.raises(ValueError, match="role address"): MODULE.validate_record(value)
    value = example(); value["api_key"] = "example"
    with pytest.raises(ValueError, match="top-level keys"): MODULE.validate_record(value)
    value = example(); value["channels"][0]["critical_escalation_minutes"] = 120
    with pytest.raises(ValueError, match="cannot be slower"): MODULE.validate_record(value)

def test_go_requires_every_channel_verified() -> None:
    value = example(); value["decision"] = "GO"
    with pytest.raises(ValueError, match="GO requires every channel"): MODULE.validate_record(value)
