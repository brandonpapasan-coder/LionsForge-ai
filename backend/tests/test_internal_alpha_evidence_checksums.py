import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "manage_internal_alpha_evidence_checksums.py"
SPEC = spec_from_file_location("manage_internal_alpha_evidence_checksums", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
build_inventory = MODULE.build_inventory
write_inventory = MODULE.write_inventory
verify_inventory = MODULE.verify_inventory


def evidence(tmp_path: Path) -> list[Path]:
    first = tmp_path / "a.txt"
    second = tmp_path / "b.json"
    first.write_text("alpha\n", encoding="utf-8")
    second.write_text('{"ok":true}\n', encoding="utf-8")
    return [second, first]


def test_inventory_is_deterministic_and_sorted(tmp_path: Path):
    files = evidence(tmp_path)
    inventory = tmp_path / "checksums.json"
    write_inventory(files, inventory)
    first = inventory.read_bytes()
    write_inventory(list(reversed(files)), inventory)
    assert inventory.read_bytes() == first
    payload = json.loads(first)
    assert payload["schema_version"] == 1
    assert [item["path"] for item in payload["files"]] == sorted(
        path.as_posix() for path in files
    )
    verify_inventory(files, inventory)


def test_verification_rejects_modified_or_missing_file(tmp_path: Path):
    files = evidence(tmp_path)
    inventory = tmp_path / "checksums.json"
    write_inventory(files, inventory)
    files[0].write_text("changed\n", encoding="utf-8")
    with pytest.raises(ValueError, match="does not match"):
        verify_inventory(files, inventory)
    files[0].unlink()
    with pytest.raises(ValueError, match="missing or not regular"):
        verify_inventory(files, inventory)


def test_rejects_duplicates_self_inventory_and_symlinks(tmp_path: Path):
    files = evidence(tmp_path)
    inventory = tmp_path / "checksums.json"
    with pytest.raises(ValueError, match="duplicate"):
        build_inventory([files[0], files[0]], inventory)
    write_inventory(files, inventory)
    with pytest.raises(ValueError, match="cannot checksum itself"):
        build_inventory([files[0], inventory], inventory)
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(files[0])
    except OSError:
        pytest.skip("symlinks are unavailable")
    with pytest.raises(ValueError, match="symlinks"):
        build_inventory([link], inventory)


def test_verification_rejects_inventory_schema_drift(tmp_path: Path):
    files = evidence(tmp_path)
    inventory = tmp_path / "checksums.json"
    write_inventory(files, inventory)
    payload = json.loads(inventory.read_text(encoding="utf-8"))
    payload["unexpected"] = True
    inventory.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="does not match"):
        verify_inventory(files, inventory)
