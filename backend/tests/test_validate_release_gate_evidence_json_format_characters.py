import importlib.util
import json
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_release_gate_evidence_json_format_characters", SCRIPT
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize(
    "character",
    [
        "\u200b",  # ZERO WIDTH SPACE
        "\u200c",  # ZERO WIDTH NON-JOINER
        "\u200d",  # ZERO WIDTH JOINER
        "\u202a",  # LEFT-TO-RIGHT EMBEDDING
        "\u202e",  # RIGHT-TO-LEFT OVERRIDE
        "\u2066",  # LEFT-TO-RIGHT ISOLATE
        "\u2069",  # POP DIRECTIONAL ISOLATE
        "\ufeff",  # ZERO WIDTH NO-BREAK SPACE
    ],
)
def test_rejects_unicode_format_characters_in_json_values(character):
    with pytest.raises(ValueError, match="JSON contains a Unicode format character"):
        MODULE._validate_json_tree({"value": f"release{character}evidence"})


@pytest.mark.parametrize(
    "character",
    ["\u200b", "\u202e", "\u2066", "\ufeff"],
)
def test_rejects_unicode_format_characters_in_json_object_keys(character):
    with pytest.raises(ValueError, match="JSON contains a Unicode format character"):
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


def test_read_evidence_rejects_format_character_value_after_json_decode(tmp_path):
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps({"value": "release\u202eevidence"}), encoding="utf-8")
    evidence.chmod(0o600)

    with pytest.raises(ValueError, match="JSON contains a Unicode format character"):
        MODULE._read_evidence(evidence)


def test_read_evidence_rejects_format_character_key_after_json_decode(tmp_path):
    evidence = tmp_path / "evidence.json"
    evidence.write_text(json.dumps({"release\u200bevidence": "value"}), encoding="utf-8")
    evidence.chmod(0o600)

    with pytest.raises(ValueError, match="JSON contains a Unicode format character"):
        MODULE._read_evidence(evidence)


def test_json_format_character_rejection_precedes_control_character_validation():
    value = "release\u202e\u0001evidence"

    with pytest.raises(ValueError, match="JSON contains a Unicode format character"):
        MODULE._validate_json_string(value)


def test_json_format_character_rejection_precedes_semantic_validation(monkeypatch):
    semantic_validation_reached = False

    def unexpected_validate_payload(*args, **kwargs):
        nonlocal semantic_validation_reached
        semantic_validation_reached = True
        raise AssertionError("semantic validation should not be reached")

    monkeypatch.setattr(MODULE, "validate_payload", unexpected_validate_payload)
    payload = {"unexpected": "release\u202eevidence"}

    with pytest.raises(ValueError, match="JSON contains a Unicode format character"):
        MODULE._validate_json_tree(payload)
    assert semantic_validation_reached is False
