import importlib.util
import json
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_release_gate_evidence_filenames", SCRIPT
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _write_evidence(path: Path, value: str = "safe") -> None:
    path.write_text(json.dumps({"value": value}), encoding="utf-8")
    path.chmod(0o600)


def test_accepts_visible_lowercase_json_filename(tmp_path):
    path = tmp_path / "release-gate-evidence.json"
    _write_evidence(path)
    assert MODULE._read_evidence(path) == {"value": "safe"}


@pytest.mark.parametrize(
    ("name", "message"),
    [
        ("evidence", "lowercase .json suffix"),
        ("evidence.JSON", "lowercase .json suffix"),
        ("evidence.json.txt", "lowercase .json suffix"),
        (".evidence.json", "must not be hidden"),
        ("-evidence.json", "must not begin with a hyphen"),
    ],
)
def test_rejects_untrusted_filename_shapes(name, message):
    with pytest.raises(ValueError, match=message):
        MODULE._validate_evidence_path(Path(name))


def test_reader_rejects_wrong_suffix_before_filesystem_access(monkeypatch):
    inspected = False

    def unexpected_lstat(self):
        nonlocal inspected
        inspected = True
        raise AssertionError("filesystem access should not be reached")

    monkeypatch.setattr(Path, "lstat", unexpected_lstat)
    with pytest.raises(ValueError, match="lowercase .json suffix"):
        MODULE._read_evidence(Path("evidence.txt"))
    assert inspected is False


def test_descriptor_helper_rejects_hidden_filename_before_open(monkeypatch):
    opened = False

    def unexpected_open(*args, **kwargs):
        nonlocal opened
        opened = True
        raise AssertionError("open should not be reached")

    monkeypatch.setattr(MODULE.os, "open", unexpected_open)
    with pytest.raises(ValueError, match="must not be hidden"):
        MODULE._open_evidence_descriptor(Path(".evidence.json"))
    assert opened is False
