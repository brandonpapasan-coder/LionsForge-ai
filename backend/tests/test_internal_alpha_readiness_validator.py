import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "validate_internal_alpha_readiness.py"
LIVE_RECORD = ROOT / "docs" / "operations" / "internal-alpha-readiness-gate.md"
SPEC = spec_from_file_location("validate_internal_alpha_readiness", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
validate_record = MODULE.validate_record


SECTIONS = [
    "## Current decision",
    "## 1. Candidate integrity",
    "## 2. Internal Alpha environment",
    "## 3. Integrated product journeys",
    "## 4. Cross-system controls",
    "## 5. Reliability, security, and operations",
    "## 6. Recovery and rollback",
    "## 7. Alpha cohort controls",
    "## 8. Final authorization",
    "## GO rule",
]


def valid_record(*, decision="GO"):
    lines = [
        "# Internal Alpha Readiness Gate",
        SECTIONS[0],
        "- Protected-main implementation merge: " + "a" * 40,
        "- Staging execution controls merge: " + "d" * 40,
        "- Pre-merge gate-clean candidate: " + "e" * 40,
        "- Backend image digest: sha256:" + "b" * 64,
        "- Frontend image digest: sha256:" + "c" * 64,
        "- Review owner role: Release Owner",
        "- Review date: 2026-07-23",
        f"- Decision: **{decision}**",
    ]
    lines.extend(SECTIONS[1:])
    lines.extend(
        [
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
    return "\n".join(lines)


def codes(text):
    return {finding.code for finding in validate_record(text)}


def test_live_no_go_record_is_structurally_valid():
    assert validate_record(LIVE_RECORD.read_text(encoding="utf-8")) == []


def test_valid_go_record_passes():
    assert validate_record(valid_record()) == []


def test_no_go_record_can_keep_pending_evidence():
    text = valid_record(decision="NO-GO").replace("Release Owner", "PENDING")
    text = text.replace("| VERIFIED |", "| NOT VERIFIED |", 1)
    assert validate_record(text) == []


def test_no_go_still_requires_baseline_fields():
    text = valid_record(decision="NO-GO").replace(
        "- Staging execution controls merge: " + "d" * 40 + "\n", ""
    )
    assert "missing-field" in codes(text)


def test_no_go_still_requires_all_sections():
    text = valid_record(decision="NO-GO").replace("## 6. Recovery and rollback\n", "")
    assert "missing-section" in codes(text)


def test_no_go_rejects_conflicting_duplicate_decisions():
    text = valid_record(decision="NO-GO").replace(
        "- Decision: **NO-GO**",
        "- Decision: **GO**\n- Decision: **NO-GO**",
    )
    assert "duplicate-field" in codes(text)


def test_record_rejects_duplicate_provenance_values():
    text = valid_record().replace(
        "- Backend image digest: sha256:" + "b" * 64,
        "- Backend image digest: sha256:"
        + "b" * 64
        + "\n- Backend image digest: sha256:"
        + "f" * 64,
    )
    assert "duplicate-field" in codes(text)


def test_invalid_decision_fails():
    text = valid_record().replace("**GO**", "**READY**")
    assert "invalid-decision" in codes(text)


def test_go_requires_exact_sha_and_digests():
    text = valid_record().replace("a" * 40, "main", 1)
    text = text.replace("sha256:" + "b" * 64, "latest", 1)
    assert {"invalid-sha", "invalid-image-digest"}.issubset(codes(text))


def test_go_rejects_pending_fields_and_controls():
    text = valid_record().replace(
        "- Review owner role: Release Owner", "- Review owner role: PENDING"
    )
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
