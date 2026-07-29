from __future__ import annotations

import copy
import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_public_data_inventory.py"
EXAMPLE = ROOT / "docs" / "public-data-inventory.example.json"
SPEC = spec_from_file_location("validate_public_data_inventory", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def example() -> dict[str, object]:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def test_example_inventory_is_complete_no_go() -> None:
    value = example()
    report = MODULE.validate_inventory(value, "0" * 40)
    assert report == {
        "candidate_sha": "0" * 40,
        "data_class_count": 9,
        "decision": "NO-GO",
        "result": "VALID",
    }


def test_inventory_rejects_missing_duplicate_and_candidate_mismatch() -> None:
    value = example()
    value["data_classes"] = value["data_classes"][:-1]
    with pytest.raises(ValueError, match="required data classes are missing"):
        MODULE.validate_inventory(value)

    value = example()
    value["data_classes"].append(copy.deepcopy(value["data_classes"][0]))
    with pytest.raises(ValueError, match="duplicate data class id"):
        MODULE.validate_inventory(value)

    with pytest.raises(ValueError, match="does not match expected candidate"):
        MODULE.validate_inventory(example(), "a" * 40)


def test_inventory_rejects_unknown_and_secret_like_keys() -> None:
    value = example()
    value["unexpected"] = True
    with pytest.raises(ValueError, match="top-level keys"):
        MODULE.validate_inventory(value)

    value = example()
    value["data_classes"][0]["api_key"] = "not-a-real-key"
    with pytest.raises(ValueError, match="forbidden secret-like key"):
        MODULE.validate_inventory(value)


def test_go_requires_every_class_verified_and_no_secret_values() -> None:
    value = example()
    value["decision"] = "GO"
    with pytest.raises(ValueError, match="GO requires VERIFIED"):
        MODULE.validate_inventory(value)

    value = example()
    value["data_classes"][0]["contains_secrets"] = True
    with pytest.raises(ValueError, match="must not inventory secret values"):
        MODULE.validate_inventory(value)
