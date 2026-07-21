import importlib.util
import json
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location("validate_release_gate_evidence_strings", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_accepts_string_at_character_limit():
    MODULE._validate_json_tree("x" * MODULE.MAX_JSON_STRING_CHARACTERS)


def test_rejects_value_beyond_character_limit():
    with pytest.raises(ValueError, match="maximum character count"):
        MODULE._validate_json_tree("x" * (MODULE.MAX_JSON_STRING_CHARACTERS + 1))


def test_rejects_key_beyond_character_limit():
    oversized_key = "k" * (MODULE.MAX_JSON_STRING_CHARACTERS + 1)
    with pytest.raises(ValueError, match="maximum character count"):
        MODULE._validate_json_tree({oversized_key: True})


def test_counts_decoded_unicode_characters_not_utf8_bytes(tmp_path):
    value = "🦁" * MODULE.MAX_JSON_STRING_CHARACTERS
    path = tmp_path / "unicode-boundary.json"
    path.write_text(json.dumps({"value": value}), encoding="utf-8")
    assert MODULE._read_evidence(path) == {"value": value}


def test_rejects_oversized_string_from_raw_file(tmp_path):
    path = tmp_path / "oversized-string.json"
    path.write_text(
        json.dumps({"value": "x" * (MODULE.MAX_JSON_STRING_CHARACTERS + 1)}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="maximum character count"):
        MODULE._read_evidence(path)
