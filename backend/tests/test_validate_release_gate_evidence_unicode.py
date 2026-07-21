import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location("validate_release_gate_evidence_unicode", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_rejects_lone_surrogates_in_json_values(tmp_path):
    for name, escaped in (
        ("high", r"\ud800"),
        ("low", r"\udfff"),
    ):
        evidence_path = tmp_path / f"lone-{name}-surrogate.json"
        evidence_path.write_text(
            f'{{"repository":"owner/{escaped}"}}',
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="invalid Unicode surrogate"):
            MODULE._read_evidence(evidence_path)


def test_rejects_lone_surrogates_in_json_keys(tmp_path):
    evidence_path = tmp_path / "surrogate-key.json"
    evidence_path.write_text(r'{"\ud800":"value"}', encoding="utf-8")
    with pytest.raises(ValueError, match="invalid Unicode surrogate"):
        MODULE._read_evidence(evidence_path)


def test_accepts_valid_supplementary_plane_character(tmp_path):
    evidence_path = tmp_path / "valid-supplementary.json"
    evidence_path.write_text(r'{"symbol":"\ud83e\udd81"}', encoding="utf-8")
    assert MODULE._read_evidence(evidence_path) == {"symbol": "🦁"}
