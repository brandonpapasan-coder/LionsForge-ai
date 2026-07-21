import importlib.util
import json
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location("validate_release_gate_evidence_breadth", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_accepts_exact_json_node_limit_for_array():
    value = [None] * (MODULE.MAX_JSON_NODES - 1)
    MODULE._validate_json_tree(value)


def test_rejects_array_beyond_json_node_limit():
    value = [None] * MODULE.MAX_JSON_NODES
    with pytest.raises(ValueError, match="maximum node count"):
        MODULE._validate_json_tree(value)


def test_counts_object_keys_and_values_toward_limit():
    accepted_width = (MODULE.MAX_JSON_NODES - 1) // 2
    MODULE._validate_json_tree({str(index): None for index in range(accepted_width)})

    rejected_width = accepted_width + 1
    with pytest.raises(ValueError, match="maximum node count"):
        MODULE._validate_json_tree(
            {str(index): None for index in range(rejected_width)}
        )


def test_rejects_wide_raw_json_file(tmp_path):
    evidence_path = tmp_path / "wide.json"
    evidence_path.write_text(
        json.dumps([None] * MODULE.MAX_JSON_NODES),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="maximum node count"):
        MODULE._read_evidence(evidence_path)
