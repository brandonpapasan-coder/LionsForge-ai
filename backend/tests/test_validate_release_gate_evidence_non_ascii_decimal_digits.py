import importlib.util
import sys
import unicodedata
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_release_gate_evidence_non_ascii_decimal_digits", SCRIPT
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize(
    "character",
    [
        "\u0660",  # Arabic-Indic digit zero
        "\u06f5",  # extended Arabic-Indic digit five
        "\u0967",  # Devanagari digit one
        "\u09e8",  # Bengali digit two
        "\uff19",  # fullwidth digit nine
    ],
)
def test_rejects_non_ascii_decimal_digits(character):
    assert unicodedata.category(character) == "Nd"
    assert character not in "0123456789"
    with pytest.raises(ValueError, match="ASCII decimal digits"):
        MODULE._validate_path_component(f"release-{character}-evidence")


@pytest.mark.parametrize(
    "component",
    [
        "release-0-evidence",
        "release-2026-07-21",
        "evidence123",
        "version-42",
    ],
)
def test_accepts_ascii_decimal_digits(component):
    MODULE._validate_path_component(component)


def test_rejects_non_ascii_digit_in_parent_component():
    with pytest.raises(ValueError, match="ASCII decimal digits"):
        MODULE._validate_evidence_path(Path("artifacts\u0661/evidence.json"))


def test_rejects_non_ascii_digit_in_filename():
    with pytest.raises(ValueError, match="ASCII decimal digits"):
        MODULE._validate_evidence_path(Path("evidence\u0968.json"))


def test_reader_rejects_non_ascii_digit_before_filesystem_access(monkeypatch):
    inspected = False

    def unexpected_lstat(self):
        nonlocal inspected
        inspected = True
        raise AssertionError("filesystem access should not be reached")

    monkeypatch.setattr(Path, "lstat", unexpected_lstat)
    with pytest.raises(ValueError, match="ASCII decimal digits"):
        MODULE._read_evidence(Path("artifacts\u0661/evidence.json"))
    assert inspected is False


def test_descriptor_helper_rejects_non_ascii_digit_before_open(monkeypatch):
    opened = False

    def unexpected_open(*args, **kwargs):
        nonlocal opened
        opened = True
        raise AssertionError("open should not be reached")

    monkeypatch.setattr(MODULE.os, "open", unexpected_open)
    with pytest.raises(ValueError, match="ASCII decimal digits"):
        MODULE._open_evidence_descriptor(Path("evidence\u0968.json"))
    assert opened is False
