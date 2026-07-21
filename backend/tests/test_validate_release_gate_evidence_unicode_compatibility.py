import importlib.util
import sys
import unicodedata
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_release_gate_evidence.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_release_gate_evidence_unicode_compatibility", SCRIPT
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize(
    "component",
    [
        "ｅｖｉｄｅｎｃｅ",  # full-width ASCII
        "eﬃdence",  # ligature
        "release①",  # enclosed alphanumeric
        "version²",  # superscript
        "artifactK",  # compatibility letter
    ],
)
def test_rejects_unicode_compatibility_forms(component):
    assert unicodedata.normalize("NFKC", component) != component
    with pytest.raises(ValueError, match="Unicode compatibility forms"):
        MODULE._validate_path_component(component)


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
def test_accepts_nfkc_stable_visible_unicode(component):
    assert unicodedata.normalize("NFKC", component) == component
    MODULE._validate_path_component(component)


def test_rejects_compatibility_form_in_parent_component():
    with pytest.raises(ValueError, match="Unicode compatibility forms"):
        MODULE._validate_evidence_path(Path("ａｒｔｉｆａｃｔｓ/evidence.json"))


def test_rejects_compatibility_form_in_filename():
    with pytest.raises(ValueError, match="Unicode compatibility forms"):
        MODULE._validate_evidence_path(Path("eﬃdence.json"))


def test_reader_rejects_compatibility_form_before_filesystem_access(monkeypatch):
    inspected = False

    def unexpected_lstat(self):
        nonlocal inspected
        inspected = True
        raise AssertionError("filesystem access should not be reached")

    monkeypatch.setattr(Path, "lstat", unexpected_lstat)
    with pytest.raises(ValueError, match="Unicode compatibility forms"):
        MODULE._read_evidence(Path("ａｒｔｉｆａｃｔｓ/evidence.json"))
    assert inspected is False


def test_descriptor_helper_rejects_compatibility_form_before_open(monkeypatch):
    opened = False

    def unexpected_open(*args, **kwargs):
        nonlocal opened
        opened = True
        raise AssertionError("open should not be reached")

    monkeypatch.setattr(MODULE.os, "open", unexpected_open)
    with pytest.raises(ValueError, match="Unicode compatibility forms"):
        MODULE._open_evidence_descriptor(Path("eﬃdence.json"))
    assert opened is False
