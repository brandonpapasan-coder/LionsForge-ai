import importlib.util
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_release_gate_evidence_unicode_variation_selectors", SCRIPT
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize(
    "selector",
    [
        "\ufe00",       # variation selector-1
        "\ufe0e",       # text presentation selector
        "\ufe0f",       # emoji presentation selector
        "\U000e0100",  # supplementary variation selector-17
        "\U000e01ef",  # supplementary variation selector-256
    ],
)
def test_rejects_unicode_variation_selectors(selector):
    with pytest.raises(ValueError, match="Unicode variation selectors"):
        MODULE._validate_path_component(f"release{selector}evidence")


@pytest.mark.parametrize(
    "component",
    [
        "release-evidence",
        "emoji-😀",
        "symbol-❤",
        "資料",
    ],
)
def test_accepts_text_and_emoji_without_variation_selectors(component):
    MODULE._validate_path_component(component)


def test_rejects_variation_selector_in_parent_component():
    with pytest.raises(ValueError, match="Unicode variation selectors"):
        MODULE._validate_evidence_path(Path("artifacts\ufe0f/evidence.json"))


def test_rejects_variation_selector_in_filename():
    with pytest.raises(ValueError, match="Unicode variation selectors"):
        MODULE._validate_evidence_path(Path("evidence\U000e0100.json"))


def test_rejects_leading_variation_selector_with_specific_error():
    with pytest.raises(ValueError, match="Unicode variation selectors"):
        MODULE._validate_path_component("\ufe0fevidence")


def test_reader_rejects_variation_selector_before_filesystem_access(monkeypatch):
    inspected = False

    def unexpected_lstat(self):
        nonlocal inspected
        inspected = True
        raise AssertionError("filesystem access should not be reached")

    monkeypatch.setattr(Path, "lstat", unexpected_lstat)
    with pytest.raises(ValueError, match="Unicode variation selectors"):
        MODULE._read_evidence(Path("artifacts\ufe0f/evidence.json"))
    assert inspected is False


def test_descriptor_helper_rejects_variation_selector_before_open(monkeypatch):
    opened = False

    def unexpected_open(*args, **kwargs):
        nonlocal opened
        opened = True
        raise AssertionError("open should not be reached")

    monkeypatch.setattr(MODULE.os, "open", unexpected_open)
    with pytest.raises(ValueError, match="Unicode variation selectors"):
        MODULE._open_evidence_descriptor(Path("evidence\U000e0100.json"))
    assert opened is False
