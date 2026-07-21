import importlib.util
import sys
import unicodedata
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_release_gate_evidence_unicode_assignment_stability", SCRIPT
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize(
    "character",
    [
        "\ue000",       # BMP private use
        "\uf8ff",       # BMP private use end
        "\U000f0000",  # supplementary private use area A
        "\U00100000",  # supplementary private use area B
    ],
)
def test_rejects_private_use_characters(character):
    assert unicodedata.category(character) == "Co"
    with pytest.raises(ValueError, match="private-use or unassigned"):
        MODULE._validate_path_component(f"release{character}evidence")


def test_rejects_unassigned_unicode_character():
    character = "\u0378"
    assert unicodedata.category(character) == "Cn"
    with pytest.raises(ValueError, match="private-use or unassigned"):
        MODULE._validate_path_component(f"release{character}evidence")


@pytest.mark.parametrize(
    "component",
    [
        "release-evidence",
        "café",
        "資料",
        "emoji-😀",
        "supplementary-𐐷",
    ],
)
def test_accepts_assigned_unicode_characters(component):
    assert all(unicodedata.category(character) not in {"Cn", "Co"} for character in component)
    MODULE._validate_path_component(component)


def test_rejects_private_use_character_in_parent_component():
    with pytest.raises(ValueError, match="private-use or unassigned"):
        MODULE._validate_evidence_path(Path("artifacts\ue000/evidence.json"))


def test_rejects_unassigned_character_in_filename():
    with pytest.raises(ValueError, match="private-use or unassigned"):
        MODULE._validate_evidence_path(Path("evidence\u0378.json"))


def test_reader_rejects_unstable_assignment_before_filesystem_access(monkeypatch):
    inspected = False

    def unexpected_lstat(self):
        nonlocal inspected
        inspected = True
        raise AssertionError("filesystem access should not be reached")

    monkeypatch.setattr(Path, "lstat", unexpected_lstat)
    with pytest.raises(ValueError, match="private-use or unassigned"):
        MODULE._read_evidence(Path("artifacts\ue000/evidence.json"))
    assert inspected is False


def test_descriptor_helper_rejects_unstable_assignment_before_open(monkeypatch):
    opened = False

    def unexpected_open(*args, **kwargs):
        nonlocal opened
        opened = True
        raise AssertionError("open should not be reached")

    monkeypatch.setattr(MODULE.os, "open", unexpected_open)
    with pytest.raises(ValueError, match="private-use or unassigned"):
        MODULE._open_evidence_descriptor(Path("evidence\u0378.json"))
    assert opened is False
