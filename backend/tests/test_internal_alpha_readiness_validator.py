import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_internal_alpha_readiness.py"
SPEC = spec_from_file_location("validate_internal_alpha_readiness", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
validate_record = MODULE.validate_record


def valid_record(*, decision="GO"):
    return "\n".join(
        [
            "# Internal Alpha Readiness Gate",
            "- Candidate commit SHA: " + "a" * 40,
            "- Candidate backend image digest: sha256:" + "b" * 64,
            "- Candidate frontend image digest: sha256:" + "c" * 64,
            "- Candidate mobile build identifier: NOT APPLICABLE",
            "- Review owner role: Release Owner",
            "- Review date: 2026-07-23",
            f"- Decision: **{decision}**",
            "| Control | Required evidence | Status |",
            "|---|---|---|",
            "| Candidate SHA exists on protected main | commit | VERIFIED |",
            "| Required CI checks passed on unchanged SHA | runs | VERIFIED |",
            "| Backend image is immutable | digest | VERIFIED |",
            "| Frontend image is immutable | digest | VERIFIED |",
            "| Dependency audit | report | PASSED |",
            "| Backend rollback to prior immutable digest | evidence | PASSED |",
            "| Product owner | owner | 2026-07-23 | APPROVED |",
            "> I verified this decision against the exact candidate SHA and immutable backend and frontend image digests recorded above.",
        ]
    )


def codes(text):
    return {finding.code for finding in validate_record(text)}


def test_valid_go_record_passes():
    assert validate_record(valid_record()) == []


def test_current_no_go_record_can_remain_incomplete():
    text = valid_record(decision="NO-GO").replace("Release Owner", "PENDING")
    text = text.replace("| VERIFIED |", "| NOT VERIFIED |", 1)
    assert validate_record(text) == []


def test_invalid_decision_fails():
    text = valid_record().replace("**GO**", "**READY**")
    assert "invalid-decision" in codes(text)


def test_go_requires_exact_sha_and_digests():
    text = valid_record().replace("a" * 40, "main", 1)
    text = text.replace("sha256:" + "b" * 64, "latest", 1)
    assert {"invalid-sha", "invalid-image-digest"}.issubset(codes(text))


def test_go_rejects_pending_fields_and_controls():
    text = valid_record().replace("- Review owner role: Release Owner", "- Review owner role: PENDING")
    text = text.replace(
        "| Dependency audit | report | PASSED |",
        "| Dependency audit | PENDING | NOT VERIFIED |",
    )
    assert {"missing-field", "incomplete-control", "incomplete-field"}.issubset(codes(text))


def test_go_rejects_open_blockers():
    text = valid_record() + "\n| Staging provisioning | BLOCKING | owner | date | OPEN |"
    assert "open-blocker" in codes(text)


def test_go_requires_provenance_signoff():
    text = valid_record().replace(
        "> I verified this decision against the exact candidate SHA and immutable backend and frontend image digests recorded above.",
        "> Approved.",
    )
    assert "missing-signoff" in codes(text)
