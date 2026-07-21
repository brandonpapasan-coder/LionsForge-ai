import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location("validate_release_gate_evidence_controls", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize(
    "escape",
    (
        r"\u0000",
        r"\n",
        r"\r",
        r"\u001f",
        r"\u007f",
        r"\u0085",
        r"\u009f",
    ),
)
def test_rejects_control_characters_in_json_values(tmp_path, escape):
    evidence_path = tmp_path / "control-value.json"
    evidence_path.write_text(f'{{"value":"safe{escape}unsafe"}}', encoding="utf-8")

    with pytest.raises(ValueError, match="control character"):
        MODULE._read_evidence(evidence_path)


@pytest.mark.parametrize("escape", (r"\u0000", r"\n", r"\u007f", r"\u0085"))
def test_rejects_control_characters_in_json_keys(tmp_path, escape):
    evidence_path = tmp_path / "control-key.json"
    evidence_path.write_text(f'{{"safe{escape}unsafe":true}}', encoding="utf-8")

    with pytest.raises(ValueError, match="control character"):
        MODULE._read_evidence(evidence_path)


def test_accepts_printable_unicode_strings(tmp_path):
    evidence_path = tmp_path / "printable.json"
    evidence_path.write_text(
        '{"message":"LionsForge AI — research validation 🦁","status":"completed"}',
        encoding="utf-8",
    )

    assert MODULE._read_evidence(evidence_path) == {
        "message": "LionsForge AI — research validation 🦁",
        "status": "completed",
    }
