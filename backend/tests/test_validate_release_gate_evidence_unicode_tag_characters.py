import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_release_gate_evidence_unicode_tag_characters", SCRIPT
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize(
    "character",
    [
        "\U000e0000",  # tag character base
        "\U000e0020",  # tag space
        "\U000e0061",  # tag latin small letter a
        "\U000e007f",  # cancel tag
    ],
)
def test_rejects_unicode_tag_characters(character):
    with pytest.raises(ValueError, match="Unicode tag characters"):
        MODULE._validate_path_component(f"release{character}evidence")


@pytest.mark.parametrize(
    "component",
    [
        "release-evidence",
        "emoji-😀",
        "資料",
        "café",
    ],
)
def test_accepts_components_without_unicode_tag_characters(component):
    MODULE._validate_path_component(component)


def test_rejects_tag_character_in_parent_component():
    with pytest.raises(ValueError, match="Unicode tag characters"):
        MODULE._validate_evidence_path(Path("artifacts\U000e0061/evidence.json"))


def test_rejects_tag_character_in_filename():
    with pytest.raises(ValueError, match="Unicode tag characters"):
        MODULE._validate_evidence_path(Path("evidence\U000e007f.json"))


def test_rejects_tag_character_with_specific_error_before_format_error():
    with pytest.raises(ValueError, match="Unicode tag characters"):
        MODULE._validate_path_component("release\U000e0061evidence")


def test_reader_rejects_tag_character_before_filesystem_access(monkeypatch):
    inspected = False

    def unexpected_lstat(self):
        nonlocal inspected
        inspected = True
        raise AssertionError("filesystem access should not be reached")

    monkeypatch.setattr(Path, "lstat", unexpected_lstat)
    with pytest.raises(ValueError, match="Unicode tag characters"):
        MODULE._read_evidence(Path("artifacts\U000e0061/evidence.json"))
    assert inspected is False


def test_descriptor_helper_rejects_tag_character_before_open(monkeypatch):
    opened = False

    def unexpected_open(*args, **kwargs):
        nonlocal opened
        opened = True
        raise AssertionError("open should not be reached")

    monkeypatch.setattr(MODULE.os, "open", unexpected_open)
    with pytest.raises(ValueError, match="Unicode tag characters"):
        MODULE._open_evidence_descriptor(Path("evidence\U000e007f.json"))
    assert opened is False
