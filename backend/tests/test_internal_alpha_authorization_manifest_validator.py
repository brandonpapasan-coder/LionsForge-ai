import copy
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_internal_alpha_authorization_manifest.py"
SPEC = spec_from_file_location("validate_internal_alpha_authorization_manifest", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
validate_manifest = MODULE.validate_manifest

SHA = "a" * 40
BACKEND_DIGEST = "sha256:" + "b" * 64
FRONTEND_DIGEST = "sha256:" + "c" * 64


def manifest() -> dict:
    gates = (
        ("Backend CI", ".github/workflows/backend-ci.yml", 101),
        ("Frontend CI", ".github/workflows/frontend-ci.yml", 102),
        ("Security Gate", ".github/workflows/security-gate.yml", 103),
        ("Deployment Validation", ".github/workflows/deployment-validation.yml", 104),
    )
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
        "gates": [
            {
                "conclusion": "success",
                "event": "push",
                "head_branch": "main",
                "head_sha": SHA,
                "html_url": f"https://github.com/owner/repo/actions/runs/{run_id}",
                "name": name,
                "path": path,
                "run_id": run_id,
                "status": "completed",
            }
            for name, path, run_id in gates
        ],
        "provenance": {
            "dispatch_ref": "refs/heads/main",
            "protected_main_sha": SHA,
            "repository": "owner/repo",
            "workflow_sha": SHA,
        },
        "schema_version": 1,
    }


def test_valid_manifest_passes():
    validate_manifest(manifest())


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (lambda value: value.update({"unexpected": True}), "manifest keys"),
        (
            lambda value: value["authorization_scope"].update({"external_staging_proven": True}),
            "repository-only boundaries",
        ),
        (
            lambda value: value["candidate"].update({"candidate_sha": "d" * 40}),
            "SHAs must match",
        ),
        (
            lambda value: value["gates"][0].update({"conclusion": "failure"}),
            "did not pass",
        ),
        (
            lambda value: value["gates"][0].update({"run_id": True}),
            "run_id is invalid",
        ),
        (
            lambda value: value["gates"].reverse(),
            "canonical order",
        ),
    ],
)
def test_invalid_manifest_is_rejected(mutator, message):
    value = copy.deepcopy(manifest())
    mutator(value)
    with pytest.raises(ValueError, match=message):
        validate_manifest(value)


def test_gate_url_must_match_repository_and_run_id():
    value = manifest()
    value["gates"][0]["html_url"] = "https://github.com/other/repo/actions/runs/101"
    with pytest.raises(ValueError, match="repository or run_id"):
        validate_manifest(value)
