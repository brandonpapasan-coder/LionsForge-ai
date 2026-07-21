import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_release_gate_evidence_parent_paths", SCRIPT
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _write_evidence(path: Path, value: str = "safe") -> None:
    path.write_text(json.dumps({"value": value}), encoding="utf-8")
    path.chmod(0o600)


def test_accepts_direct_file_path(tmp_path):
    path = tmp_path / "evidence.json"
    _write_evidence(path)
    assert MODULE._read_evidence(path) == {"value": "safe"}


def test_accepts_nested_ordinary_directory_path(tmp_path):
    directory = tmp_path / "one" / "two"
    directory.mkdir(parents=True)
    path = directory / "evidence.json"
    _write_evidence(path)
    assert MODULE._read_evidence(path) == {"value": "safe"}


def test_rejects_symlinked_immediate_parent(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    path = target / "evidence.json"
    _write_evidence(path)
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("directory symlinks are unavailable")

    with pytest.raises(ValueError, match="parent path must not contain symbolic links"):
        MODULE._read_evidence(alias / "evidence.json")


def test_rejects_symlinked_ancestor_directory(tmp_path):
    target = tmp_path / "target"
    nested = target / "nested"
    nested.mkdir(parents=True)
    path = nested / "evidence.json"
    _write_evidence(path)
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("directory symlinks are unavailable")

    with pytest.raises(ValueError, match="parent path must not contain symbolic links"):
        MODULE._read_evidence(alias / "nested" / "evidence.json")


def test_rejects_non_directory_parent_component(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory", encoding="utf-8")
    with pytest.raises(ValueError, match="parent path components must be directories"):
        MODULE._validate_parent_components(blocker / "evidence.json")


def test_relative_path_parent_chain_is_checked(tmp_path, monkeypatch):
    target = tmp_path / "target"
    target.mkdir()
    path = target / "evidence.json"
    _write_evidence(path)
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("directory symlinks are unavailable")

    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="parent path must not contain symbolic links"):
        MODULE._read_evidence(Path("alias") / "evidence.json")
