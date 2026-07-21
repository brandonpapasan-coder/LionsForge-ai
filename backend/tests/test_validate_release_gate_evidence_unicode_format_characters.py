import importlib.util
import sys
import unicodedata
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_release_gate_evidence_unicode_format_characters", SCRIPT
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize(
    "character",
    [
        "\u200b",  # zero width space
        "\u200c",  # zero width non-joiner
        "\u200d",  # zero width joiner
        "\u202a",  # left-to-right embedding
        "\u202e",  # right-to-left override
        "\u2066",  # left-to-right isolate
        "\u2069",  # pop directional isolate
        "\ufeff",  # byte-order mark / zero width no-break space
    ],
)
def test_rejects_unicode_format_characters(character):
    assert unicodedata.category(character) == "Cf"
    with pytest.raises(ValueError, match="Unicode format characters"):
        MODULE._validate_path_component(f"release{character}evidence")


@pytest.mark.parametrize(
    "component",
    [
        "café",
        "Δοκιμή",
        "данные",
        "資料",
        "release-gate_evidence.json",
    ],
)
def test_accepts_visible_normalized_unicode(component):
    MODULE._validate_path_component(component)


def test_rejects_format_character_in_parent_component():
    with pytest.raises(ValueError, match="Unicode format characters"):
        MODULE._validate_evidence_path(Path("arti\u200bfacts/evidence.json"))


def test_rejects_format_character_in_filename():
    with pytest.raises(ValueError, match="Unicode format characters"):
        MODULE._validate_evidence_path(Path("evidence\u202e.json"))


def test_reader_rejects_format_character_before_filesystem_access(monkeypatch):
    inspected = False

    def unexpected_lstat(self):
        nonlocal inspected
        inspected = True
        raise AssertionError("filesystem access should not be reached")

    monkeypatch.setattr(Path, "lstat", unexpected_lstat)
    with pytest.raises(ValueError, match="Unicode format characters"):
        MODULE._read_evidence(Path("arti\u200bfacts/evidence.json"))
    assert inspected is False


def test_descriptor_helper_rejects_format_character_before_open(monkeypatch):
    opened = False

    def unexpected_open(*args, **kwargs):
        nonlocal opened
        opened = True
        raise AssertionError("open should not be reached")

    monkeypatch.setattr(MODULE.os, "open", unexpected_open)
    with pytest.raises(ValueError, match="Unicode format characters"):
        MODULE._open_evidence_descriptor(Path("evidence\ufeff.json"))
    assert opened is False
