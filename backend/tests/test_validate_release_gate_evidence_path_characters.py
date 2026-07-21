import importlib.util
import json
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_release_gate_evidence_path_characters", SCRIPT
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _write_evidence(path: Path, value: str = "safe") -> None:
    path.write_text(json.dumps({"value": value}), encoding="utf-8")
    path.chmod(0o600)


def test_accepts_nfc_unicode_component(tmp_path):
    directory = tmp_path / "café"
    directory.mkdir()
    path = directory / "evidence.json"
    _write_evidence(path)
    assert MODULE._read_evidence(path) == {"value": "safe"}


@pytest.mark.parametrize(
    ("path", "message"),
    [
        (Path("bad\nname.json"), "control characters"),
        (Path("folder.") / "evidence.json", "space or dot"),
        (Path("folder ") / "evidence.json", "space or dot"),
        (Path("cafe\u0301") / "evidence.json", "NFC Unicode normalization"),
        (Path("a" * 256) / "evidence.json", "maximum UTF-8 byte length"),
        (Path("bad\ud800") / "evidence.json", "valid Unicode scalars"),
    ],
)
def test_rejects_ambiguous_path_components(path, message):
    with pytest.raises(ValueError, match=message):
        MODULE._validate_evidence_path(path)


def test_multibyte_component_limit_is_measured_in_utf8_bytes():
    path = Path("é" * 128) / "evidence.json"
    with pytest.raises(ValueError, match="maximum UTF-8 byte length"):
        MODULE._validate_evidence_path(path)


def test_character_validation_occurs_before_filesystem_access(monkeypatch):
    inspected = False

    def unexpected_lstat(self):
        nonlocal inspected
        inspected = True
        raise AssertionError("filesystem access should not be reached")

    monkeypatch.setattr(Path, "lstat", unexpected_lstat)
    with pytest.raises(ValueError, match="control characters"):
        MODULE._read_evidence(Path("bad\tname.json"))
    assert inspected is False
