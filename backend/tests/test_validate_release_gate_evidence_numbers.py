import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location("validate_release_gate_evidence_numbers", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_accepts_integer_at_exact_digit_limit(tmp_path):
    evidence_path = tmp_path / "bounded-integer.json"
    value = "9" * MODULE.MAX_JSON_INTEGER_DIGITS
    evidence_path.write_text(f'{{"run_id":{value}}}', encoding="utf-8")

    assert MODULE._read_evidence(evidence_path) == {"run_id": int(value)}


def test_rejects_positive_and_negative_integers_beyond_digit_limit(tmp_path):
    oversized = "9" * (MODULE.MAX_JSON_INTEGER_DIGITS + 1)
    for prefix, filename in (("", "positive.json"), ("-", "negative.json")):
        evidence_path = tmp_path / filename
        evidence_path.write_text(
            f'{{"run_id":{prefix}{oversized}}}',
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="maximum digit count"):
            MODULE._read_evidence(evidence_path)


def test_rejects_decimal_and_exponent_notation(tmp_path):
    for literal, filename in (("1.0", "decimal.json"), ("1e3", "exponent.json")):
        evidence_path = tmp_path / filename
        evidence_path.write_text(f'{{"run_id":{literal}}}', encoding="utf-8")
        with pytest.raises(ValueError, match="unsupported floating-point value"):
            MODULE._read_evidence(evidence_path)


def test_numeric_hooks_reject_before_schema_validation(tmp_path):
    evidence_path = tmp_path / "nested-float.json"
    evidence_path.write_text('{"gates":[{"run_id":0.5}]}', encoding="utf-8")

    with pytest.raises(ValueError, match="unsupported floating-point value: 0.5"):
        MODULE._read_evidence(evidence_path)
