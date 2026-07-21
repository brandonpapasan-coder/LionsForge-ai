import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_release_gate_evidence_path_canonicality", SCRIPT
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _write_evidence(path: Path, value: str = "safe") -> None:
    path.write_text(json.dumps({"value": value}), encoding="utf-8")
    path.chmod(0o600)


def test_accepts_ordinary_absolute_path(tmp_path):
    path = tmp_path / "evidence.json"
    _write_evidence(path)
    assert MODULE._read_evidence(path) == {"value": "safe"}


def test_accepts_ordinary_relative_path(tmp_path, monkeypatch):
    path = tmp_path / "evidence.json"
    _write_evidence(path)
    monkeypatch.chdir(tmp_path)
    assert MODULE._read_evidence(Path("evidence.json")) == {"value": "safe"}


@pytest.mark.parametrize("path", [Path("."), Path("/"), Path("")])
def test_rejects_paths_that_do_not_identify_a_file(path):
    with pytest.raises(ValueError, match="must identify a file"):
        MODULE._validate_evidence_path(path)


@pytest.mark.parametrize(
    "path",
    [
        Path("../evidence.json"),
        Path("folder/../evidence.json"),
        Path("one/two/../../evidence.json"),
    ],
)
def test_rejects_parent_traversal_components(path):
    with pytest.raises(ValueError, match="parent traversal components"):
        MODULE._validate_evidence_path(path)


def test_reader_rejects_parent_traversal_before_filesystem_access(tmp_path, monkeypatch):
    target = tmp_path / "evidence.json"
    _write_evidence(target)
    nested = tmp_path / "nested"
    nested.mkdir()
    monkeypatch.chdir(nested)

    with pytest.raises(ValueError, match="parent traversal components"):
        MODULE._read_evidence(Path("../evidence.json"))


def test_descriptor_helper_rejects_parent_traversal_directly(tmp_path, monkeypatch):
    target = tmp_path / "evidence.json"
    _write_evidence(target)
    nested = tmp_path / "nested"
    nested.mkdir()
    monkeypatch.chdir(nested)

    with pytest.raises(ValueError, match="parent traversal components"):
        MODULE._open_evidence_descriptor(Path("../evidence.json"))


def test_path_validation_occurs_before_open(monkeypatch):
    opened = False

    def unexpected_open(*args, **kwargs):
        nonlocal opened
        opened = True
        raise AssertionError("open should not be reached")

    monkeypatch.setattr(MODULE.os, "open", unexpected_open)
    with pytest.raises(ValueError, match="parent traversal components"):
        MODULE._open_evidence_descriptor(Path("../evidence.json"))
    assert opened is False
