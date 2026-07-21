import importlib.util
import json
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_release_gate_evidence_json_variation_selectors", SCRIPT
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize(
    "character",
    [
        "\ufe00",
        "\ufe0f",
        "\U000e0100",
        "\U000e01ef",
    ],
)
def test_rejects_unicode_variation_selectors_in_json_values(character):
    with pytest.raises(ValueError, match="JSON contains a Unicode variation selector"):
        MODULE._validate_json_tree({"value": f"release{character}evidence"})


@pytest.mark.parametrize("character", ["\ufe00", "\ufe0f", "\U000e0100", "\U000e01ef"])
def test_rejects_unicode_variation_selectors_in_json_object_keys(character):
    with pytest.raises(ValueError, match="JSON contains a Unicode variation selector"):
        MODULE._validate_json_tree({f"release{character}evidence": "value"})


@pytest.mark.parametrize(
    "value",
    [
        "release-evidence",
        "café",
        "資料",
        "emoji-😀",
        "supplementary-𐐷",
    ],
)
def test_accepts_ordinary_assigned_unicode_json_strings(value):
    MODULE._validate_json_tree({"key": value, value: "accepted"})


def test_read_evidence_rejects_bmp_variation_selector_value(tmp_path):
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps({"value": "release\ufe0fevidence"}), encoding="utf-8")
    evidence.chmod(0o600)

    with pytest.raises(ValueError, match="JSON contains a Unicode variation selector"):
        MODULE._read_evidence(evidence)


def test_read_evidence_rejects_supplementary_variation_selector_key(tmp_path):
    evidence = tmp_path / "evidence.json"
    evidence.write_text(
        json.dumps({"release\U000e0100evidence": "value"}), encoding="utf-8"
    )
    evidence.chmod(0o600)

    with pytest.raises(ValueError, match="JSON contains a Unicode variation selector"):
        MODULE._read_evidence(evidence)


def test_variation_selector_rejection_precedes_control_character_validation():
    value = "release\ufe0f\u0001evidence"

    with pytest.raises(ValueError, match="JSON contains a Unicode variation selector"):
        MODULE._validate_json_string(value)


def test_variation_selector_rejection_precedes_semantic_validation(monkeypatch):
    semantic_validation_reached = False

    def unexpected_validate_payload(*args, **kwargs):
        nonlocal semantic_validation_reached
        semantic_validation_reached = True
        raise AssertionError("semantic validation should not be reached")

    monkeypatch.setattr(MODULE, "validate_payload", unexpected_validate_payload)
    payload = {"unexpected": "release\ufe0fevidence"}

    with pytest.raises(ValueError, match="JSON contains a Unicode variation selector"):
        MODULE._validate_json_tree(payload)
    assert semantic_validation_reached is False
