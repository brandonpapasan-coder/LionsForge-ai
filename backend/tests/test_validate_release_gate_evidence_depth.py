import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_release_gate_evidence_depth",
    SCRIPT,
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def nested_list(depth: int):
    value = "leaf"
    for _ in range(depth - 1):
        value = [value]
    return value


def test_accepts_tree_at_maximum_depth():
    MODULE._validate_json_tree(nested_list(MODULE.MAX_JSON_DEPTH))


def test_rejects_tree_beyond_maximum_depth():
    with pytest.raises(ValueError, match="maximum nesting depth"):
        MODULE._validate_json_tree(nested_list(MODULE.MAX_JSON_DEPTH + 1))


def test_rejects_excessively_nested_raw_json(tmp_path):
    evidence_path = tmp_path / "deep.json"
    depth = MODULE.MAX_JSON_DEPTH + 1
    evidence_path.write_text("[" * depth + "0" + "]" * depth, encoding="utf-8")

    with pytest.raises(ValueError, match="maximum nesting depth"):
        MODULE._read_evidence(evidence_path)


def test_normalizes_json_decoder_recursion_failure(tmp_path, monkeypatch):
    evidence_path = tmp_path / "recursion.json"
    evidence_path.write_text("{}", encoding="utf-8")

    def recurse(*args, **kwargs):
        raise RecursionError("decoder recursion")

    monkeypatch.setattr(MODULE.json, "loads", recurse)
    with pytest.raises(ValueError, match="parser safety limits"):
        MODULE._read_evidence(evidence_path)
