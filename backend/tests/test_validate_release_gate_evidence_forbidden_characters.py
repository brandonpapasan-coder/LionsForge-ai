import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_release_gate_evidence_forbidden_characters", SCRIPT
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize(
    "character",
    ["<", ">", ":", '"', "|", "?", "*", "\\"],
)
def test_rejects_portable_forbidden_characters(character):
    component = f"bad{character}name"
    with pytest.raises(ValueError, match="forbidden portable character"):
        MODULE._validate_path_component(component)


@pytest.mark.parametrize(
    "component",
    [
        "release-gate_evidence.json",
        "artifact (final)",
        "name+version",
        "data@host",
        "café",
    ],
)
def test_accepts_safe_portable_characters(component):
    MODULE._validate_path_component(component)


def test_rejects_forbidden_parent_component():
    with pytest.raises(ValueError, match="forbidden portable character"):
        MODULE._validate_evidence_path(Path("bad:name/evidence.json"))


def test_rejects_forbidden_filename_component():
    with pytest.raises(ValueError, match="forbidden portable character"):
        MODULE._validate_evidence_path(Path("evidence?.json"))


def test_backslash_is_rejected_as_cross_platform_separator_ambiguity():
    with pytest.raises(ValueError, match="forbidden portable character"):
        MODULE._validate_evidence_path(Path(r"folder\evidence.json"))


def test_reader_rejects_forbidden_character_before_filesystem_access(monkeypatch):
    inspected = False

    def unexpected_lstat(self):
        nonlocal inspected
        inspected = True
        raise AssertionError("filesystem access should not be reached")

    monkeypatch.setattr(Path, "lstat", unexpected_lstat)
    with pytest.raises(ValueError, match="forbidden portable character"):
        MODULE._read_evidence(Path("bad:name/evidence.json"))
    assert inspected is False


def test_descriptor_helper_rejects_forbidden_character_before_open(monkeypatch):
    opened = False

    def unexpected_open(*args, **kwargs):
        nonlocal opened
        opened = True
        raise AssertionError("open should not be reached")

    monkeypatch.setattr(MODULE.os, "open", unexpected_open)
    with pytest.raises(ValueError, match="forbidden portable character"):
        MODULE._open_evidence_descriptor(Path("evidence?.json"))
    assert opened is False
