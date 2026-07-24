import copy
import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "manage_internal_alpha_authorization_receipt.py"
SPEC = spec_from_file_location("manage_internal_alpha_authorization_receipt", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
build_receipt = MODULE.build_receipt
write_receipt = MODULE.write_receipt
verify_receipt = MODULE.verify_receipt

SHA = "a" * 40
BACKEND_DIGEST = "sha256:" + "b" * 64
FRONTEND_DIGEST = "sha256:" + "c" * 64


def manifest() -> dict:
    return {
        "authorization_scope": {
            "external_staging_proven": False,
            "public_access_authorized": False,
            "repository_only": True,
        },
        "candidate": {
            "backend_digest": BACKEND_DIGEST,
            "candidate_sha": SHA,
            "frontend_digest": FRONTEND_DIGEST,
        },
        "gates": [],
        "provenance": {
            "dispatch_ref": "refs/heads/main",
            "protected_main_sha": SHA,
            "repository": "owner/repo",
            "workflow_sha": SHA,
        },
        "schema_version": 1,
    }


def inventory() -> dict:
    return {
        "files": [
            {"path": "a.txt", "sha256": "d" * 64, "size_bytes": 10},
            {"path": "b.txt", "sha256": "e" * 64, "size_bytes": 20},
        ],
        "schema_version": 1,
    }


def write_sources(tmp_path: Path) -> tuple[Path, Path, Path]:
    manifest_path = tmp_path / "manifest.json"
    inventory_path = tmp_path / "inventory.json"
    receipt_path = tmp_path / "receipt.json"
    manifest_path.write_text(json.dumps(manifest(), sort_keys=True), encoding="utf-8")
    inventory_path.write_text(json.dumps(inventory(), sort_keys=True), encoding="utf-8")
    return manifest_path, inventory_path, receipt_path


def test_receipt_is_deterministic_and_verifiable(tmp_path: Path):
    manifest_path, inventory_path, receipt_path = write_sources(tmp_path)
    write_receipt(manifest_path, inventory_path, receipt_path)
    first = receipt_path.read_bytes()
    write_receipt(manifest_path, inventory_path, receipt_path)
    assert receipt_path.read_bytes() == first
    payload = json.loads(first)
    assert payload["candidate"]["repository"] == "owner/repo"
    assert payload["candidate"]["candidate_sha"] == SHA
    assert payload["bindings"]["inventory_file_count"] == 2
    verify_receipt(manifest_path, inventory_path, receipt_path)


@pytest.mark.parametrize("source", ["manifest", "inventory"])
def test_verification_rejects_bound_source_mutation(tmp_path: Path, source: str):
    manifest_path, inventory_path, receipt_path = write_sources(tmp_path)
    write_receipt(manifest_path, inventory_path, receipt_path)
    path = manifest_path if source == "manifest" else inventory_path
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="does not match"):
        verify_receipt(manifest_path, inventory_path, receipt_path)


def test_rejects_weakened_boundaries_and_invalid_candidate(tmp_path: Path):
    manifest_path, inventory_path, receipt_path = write_sources(tmp_path)
    value = manifest()
    value["authorization_scope"]["public_access_authorized"] = True
    manifest_path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="repository-only boundaries"):
        build_receipt(manifest_path, inventory_path, receipt_path)

    value = manifest()
    value["candidate"]["candidate_sha"] = "not-a-sha"
    manifest_path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="candidate SHA"):
        build_receipt(manifest_path, inventory_path, receipt_path)


def test_rejects_inventory_schema_drift_and_boolean_sizes(tmp_path: Path):
    manifest_path, inventory_path, receipt_path = write_sources(tmp_path)
    value = copy.deepcopy(inventory())
    value["unexpected"] = True
    inventory_path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="inventory keys"):
        build_receipt(manifest_path, inventory_path, receipt_path)

    value = inventory()
    value["files"][0]["size_bytes"] = True
    inventory_path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="size_bytes"):
        build_receipt(manifest_path, inventory_path, receipt_path)


def test_rejects_receipt_schema_drift_and_self_binding(tmp_path: Path):
    manifest_path, inventory_path, receipt_path = write_sources(tmp_path)
    write_receipt(manifest_path, inventory_path, receipt_path)
    value = json.loads(receipt_path.read_text(encoding="utf-8"))
    value["unexpected"] = True
    receipt_path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="does not match"):
        verify_receipt(manifest_path, inventory_path, receipt_path)
    with pytest.raises(ValueError, match="cannot bind itself"):
        build_receipt(receipt_path, inventory_path, receipt_path)
