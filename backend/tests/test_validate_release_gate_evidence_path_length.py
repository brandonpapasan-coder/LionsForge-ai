import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_release_gate_evidence_path_length", SCRIPT
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_accepts_ordinary_path():
    MODULE._validate_evidence_path(Path("artifacts/release-gate-evidence.json"))


def test_accepts_path_at_exact_utf8_byte_limit(monkeypatch):
    path = Path("folder/evidence.json")
    monkeypatch.setattr(MODULE, "MAX_PATH_BYTES", len(str(path).encode("utf-8")))
    MODULE._validate_evidence_path(path)


def test_rejects_path_one_byte_over_limit(monkeypatch):
    path = Path("folder/evidence.json")
    monkeypatch.setattr(MODULE, "MAX_PATH_BYTES", len(str(path).encode("utf-8")) - 1)
    with pytest.raises(ValueError, match="maximum UTF-8 byte length"):
        MODULE._validate_evidence_path(path)


def test_total_limit_is_measured_in_utf8_bytes(monkeypatch):
    path = Path("café/evidence.json")
    encoded_length = len(str(path).encode("utf-8"))
    character_length = len(str(path))
    assert encoded_length > character_length
    monkeypatch.setattr(MODULE, "MAX_PATH_BYTES", character_length)
    with pytest.raises(ValueError, match="maximum UTF-8 byte length"):
        MODULE._validate_evidence_path(path)


def test_invalid_unicode_scalar_is_rejected_during_total_length_encoding():
    with pytest.raises(ValueError, match="valid Unicode scalars"):
        MODULE._validate_evidence_path(Path("bad\ud800/evidence.json"))


def test_reader_rejects_long_path_before_filesystem_access(monkeypatch):
    inspected = False

    def unexpected_lstat(self):
        nonlocal inspected
        inspected = True
        raise AssertionError("filesystem access should not be reached")

    path = Path("folder/evidence.json")
    monkeypatch.setattr(MODULE, "MAX_PATH_BYTES", 1)
    monkeypatch.setattr(Path, "lstat", unexpected_lstat)
    with pytest.raises(ValueError, match="maximum UTF-8 byte length"):
        MODULE._read_evidence(path)
    assert inspected is False


def test_descriptor_helper_rejects_long_path_before_open(monkeypatch):
    opened = False

    def unexpected_open(*args, **kwargs):
        nonlocal opened
        opened = True
        raise AssertionError("open should not be reached")

    path = Path("folder/evidence.json")
    monkeypatch.setattr(MODULE, "MAX_PATH_BYTES", 1)
    monkeypatch.setattr(MODULE.os, "open", unexpected_open)
    with pytest.raises(ValueError, match="maximum UTF-8 byte length"):
        MODULE._open_evidence_descriptor(path)
    assert opened is False
