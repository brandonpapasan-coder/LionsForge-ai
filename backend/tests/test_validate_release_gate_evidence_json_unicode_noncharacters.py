import importlib.util
import json
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_release_gate_evidence_json_unicode_noncharacters", SCRIPT
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize(
    "character",
    [
        "\ufdd0",
        "\ufdef",
        "\ufffe",
        "\uffff",
        "\U0001fffe",
        "\U0001ffff",
        "\U0010fffe",
        "\U0010ffff",
    ],
)
def test_rejects_unicode_noncharacters_in_json_values(character):
    with pytest.raises(ValueError, match="JSON contains a Unicode noncharacter"):
        MODULE._validate_json_tree({"value": f"release{character}evidence"})


@pytest.mark.parametrize(
    "character",
    ["\ufdd0", "\uffff", "\U0001fffe", "\U0010ffff"],
)
def test_rejects_unicode_noncharacters_in_json_object_keys(character):
    with pytest.raises(ValueError, match="JSON contains a Unicode noncharacter"):
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


def test_read_evidence_rejects_noncharacter_value_after_json_decode(tmp_path):
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps({"value": "release\ufdd0evidence"}), encoding="utf-8")
    evidence.chmod(0o600)

    with pytest.raises(ValueError, match="JSON contains a Unicode noncharacter"):
        MODULE._read_evidence(evidence)


def test_read_evidence_rejects_noncharacter_key_after_json_decode(tmp_path):
    evidence = tmp_path / "evidence.json"
    evidence.write_text(
        json.dumps({"release\U0010ffffevidence": "value"}), encoding="utf-8"
    )
    evidence.chmod(0o600)

    with pytest.raises(ValueError, match="JSON contains a Unicode noncharacter"):
        MODULE._read_evidence(evidence)


def test_json_noncharacter_rejection_precedes_semantic_validation(monkeypatch):
    semantic_validation_reached = False

    def unexpected_validate_payload(*args, **kwargs):
        nonlocal semantic_validation_reached
        semantic_validation_reached = True
        raise AssertionError("semantic validation should not be reached")

    monkeypatch.setattr(MODULE, "validate_payload", unexpected_validate_payload)
    payload = {"unexpected": "release\ufdd0evidence"}

    with pytest.raises(ValueError, match="JSON contains a Unicode noncharacter"):
        MODULE._validate_json_tree(payload)
    assert semantic_validation_reached is False
