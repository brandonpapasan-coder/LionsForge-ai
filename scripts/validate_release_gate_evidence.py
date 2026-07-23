#!/usr/bin/env python3
"""Validate persisted release-gate evidence independently of the API verifier."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

_CORE_PATH = Path(__file__).with_name("validate_release_gate_evidence_core.py")
_CORE_SPEC = importlib.util.spec_from_file_location(
    "_lionsforge_release_gate_evidence_core", _CORE_PATH
)
if _CORE_SPEC is None or _CORE_SPEC.loader is None:
    raise ImportError(f"unable to load release-gate validator core from {_CORE_PATH}")
_CORE = importlib.util.module_from_spec(_CORE_SPEC)
sys.modules[_CORE_SPEC.name] = _CORE
_CORE_SPEC.loader.exec_module(_CORE)


def _validate_json_string(value: str) -> None:
    if len(value) > _CORE.MAX_JSON_STRING_CHARACTERS:
        raise ValueError(
            "evidence JSON string exceeds the maximum character count of "
            f"{_CORE.MAX_JSON_STRING_CHARACTERS}"
        )
    if _CORE._contains_surrogate(value):
        raise ValueError("evidence JSON contains an invalid Unicode surrogate")
    if _CORE._contains_unicode_noncharacter(value):
        raise ValueError("evidence JSON contains a Unicode noncharacter")
    if _CORE._contains_format_character(value):
        raise ValueError("evidence JSON contains a Unicode format character")
    if _CORE._contains_unstable_unicode_assignment(value):
        raise ValueError("evidence JSON contains private-use or unassigned Unicode characters")
    if _CORE._contains_unicode_variation_selector(value):
        raise ValueError("evidence JSON contains a Unicode variation selector")
    if _CORE._contains_control_character(value):
        raise ValueError("evidence JSON contains a control character")


setattr(_CORE, "_validate_json_string", _validate_json_string)

for _name in dir(_CORE):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_CORE, _name)
globals()["_validate_json_string"] = _validate_json_string


class _CoreProxyModule(ModuleType):
    """Keep public-module monkeypatches synchronized with the loaded core."""

    def __setattr__(self, name: str, value: object) -> None:
        if name not in {"_CORE", "__class__"} and not name.startswith("__"):
            setattr(_CORE, name, value)
        super().__setattr__(name, value)

    def __delattr__(self, name: str) -> None:
        if name not in {"_CORE", "__class__"} and not name.startswith("__"):
            if hasattr(_CORE, name):
                delattr(_CORE, name)
        super().__delattr__(name)


sys.modules[__name__].__class__ = _CoreProxyModule


if __name__ == "__main__":
    raise SystemExit(_CORE.main())
