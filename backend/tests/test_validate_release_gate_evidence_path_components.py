import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_release_gate_evidence_path_components", SCRIPT
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _path_with_components(count: int, absolute: bool = False) -> Path:
    components = [f"d{index}" for index in range(count - 1)] + ["evidence.json"]
    path = Path(*components)
    return Path("/") / path if absolute else path


def test_accepts_ordinary_component_count():
    MODULE._validate_evidence_path(Path("artifacts/release-gate-evidence.json"))


def test_accepts_exact_component_limit(monkeypatch):
    monkeypatch.setattr(MODULE, "MAX_PATH_COMPONENTS", 4)
    MODULE._validate_evidence_path(_path_with_components(4))


def test_rejects_one_component_over_limit(monkeypatch):
    monkeypatch.setattr(MODULE, "MAX_PATH_COMPONENTS", 4)
    with pytest.raises(ValueError, match="maximum component count"):
        MODULE._validate_evidence_path(_path_with_components(5))


def test_absolute_anchor_is_not_counted(monkeypatch):
    monkeypatch.setattr(MODULE, "MAX_PATH_COMPONENTS", 3)
    MODULE._validate_evidence_path(_path_with_components(3, absolute=True))


def test_relative_and_absolute_paths_apply_same_non_anchor_limit(monkeypatch):
    monkeypatch.setattr(MODULE, "MAX_PATH_COMPONENTS", 2)
    for path in (_path_with_components(3), _path_with_components(3, absolute=True)):
        with pytest.raises(ValueError, match="maximum component count"):
            MODULE._validate_evidence_path(path)


def test_reader_rejects_excessive_depth_before_filesystem_access(monkeypatch):
    inspected = False

    def unexpected_lstat(self):
        nonlocal inspected
        inspected = True
        raise AssertionError("filesystem access should not be reached")

    monkeypatch.setattr(MODULE, "MAX_PATH_COMPONENTS", 1)
    monkeypatch.setattr(Path, "lstat", unexpected_lstat)
    with pytest.raises(ValueError, match="maximum component count"):
        MODULE._read_evidence(Path("folder/evidence.json"))
    assert inspected is False


def test_descriptor_helper_rejects_excessive_depth_before_open(monkeypatch):
    opened = False

    def unexpected_open(*args, **kwargs):
        nonlocal opened
        opened = True
        raise AssertionError("open should not be reached")

    monkeypatch.setattr(MODULE, "MAX_PATH_COMPONENTS", 1)
    monkeypatch.setattr(MODULE.os, "open", unexpected_open)
    with pytest.raises(ValueError, match="maximum component count"):
        MODULE._open_evidence_descriptor(Path("folder/evidence.json"))
    assert opened is False
