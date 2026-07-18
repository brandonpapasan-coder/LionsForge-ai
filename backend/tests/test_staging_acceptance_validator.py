import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_staging_acceptance.py"
SPEC = spec_from_file_location("validate_staging_acceptance", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
validate_record = MODULE.validate_record


def valid_record(*, decision="GO", critical="0", high="0"):
    automated = [
        "Backend CI",
        "Frontend CI",
        "Security Gate",
        "Deployment Validation",
        "Staging Deploy",
        "Authenticated smoke test",
        "OpenAI provider health",
        "Mentor schema validation",
    ]
    infrastructure = [
        "Kubernetes cluster and namespace",
        "Ingress, DNS, and HTTPS",
        "PostgreSQL connectivity",
        "Database backup and restore test",
        "GHCR image-pull access",
        "Error and latency observability",
        "Acceptance user provisioned",
    ]
    manual = [
        "Sign in and load Executive Dashboard",
        "Create research project and save notebook",
        "Create and reopen research session",
        "Open Mentor with resolved research context",
        "Receive complete evidence-first Mentor response",
        "Reopen and continue Mentor conversation",
        "Start and complete Education lesson",
        "Verify market-learning panels and disclaimers",
        "Sign out and sign back in",
        "Verify persisted research, mentor, education, and learning state",
        "Execute rollback verification",
    ]
    lines = [
        "# Acceptance",
        "- Release candidate SHA: " + "a" * 40,
        "- Staging deploy workflow run: 12345",
        "- Staging URL: https://staging.example.test",
        "- Acceptance date/time (UTC): 2026-07-18T18:00:00Z",
        "- Acceptance owner: Release Owner",
        "- Backend image digest: sha256:" + "c" * 64,
        "- Running backend image digest verified: Yes",
        "- Previous deployable image SHA: " + "b" * 40,
        "- Database migration revision before deploy: rev-before",
        "- Database migration revision after deploy: rev-after",
        "| Gate | Result | Evidence | Notes |",
        "|---|---|---|---|",
    ]
    lines.extend(f"| {name} | Passed | ref | |" for name in automated)
    lines.extend(["| Check | Result | Owner | Notes |", "|---|---|---|---|"])
    lines.extend(f"| {name} | Passed | owner | |" for name in infrastructure)
    lines.extend(["| Step | Result | Evidence | Notes |", "|---|---|---|---|"])
    lines.extend(f"| {name} | Passed | ref | |" for name in manual)
    lines.extend(
        [
            "- Previous image successfully identified: Yes",
            "- Migration boundary reviewed: Yes",
            "- Rollback command or workflow executed: Yes",
            "- Service health restored after rollback: Yes",
            "- Forward redeploy completed after rollback test: Yes",
            f"- Decision: {decision}",
            "- Decision owner: Release Owner",
            "- Decision timestamp (UTC): 2026-07-18T18:30:00Z",
            f"- Unresolved critical defects: {critical}",
            f"- Unresolved high-severity defects: {high}",
            "> I verified that this decision is based on the exact release candidate SHA and backend image digest recorded above.",
        ]
    )
    return "\n".join(lines)


def codes(text):
    return {finding.code for finding in validate_record(text)}


def test_valid_go_record_passes():
    assert validate_record(valid_record()) == []


def test_invalid_sha_and_pending_gate_fail():
    text = valid_record().replace("a" * 40, "main", 1).replace(
        "| Backend CI | Passed |", "| Backend CI | Pending |"
    )
    assert {"invalid-sha", "incomplete-check"}.issubset(codes(text))


def test_invalid_or_unverified_image_digest_fails():
    text = valid_record().replace("sha256:" + "c" * 64, "latest", 1).replace(
        "- Running backend image digest verified: Yes",
        "- Running backend image digest verified: No",
    )
    assert {"invalid-image-digest", "image-provenance-unverified"}.issubset(codes(text))


def test_go_rejects_unresolved_critical_or_high_defects():
    findings = validate_record(valid_record(critical="1", high="ISSUE-42"))
    assert [finding.code for finding in findings].count("blocking-defect") == 2


def test_no_go_allows_documented_blocking_defects():
    assert validate_record(valid_record(decision="NO-GO", critical="1", high="ISSUE-42")) == []


def test_incomplete_rollback_is_rejected():
    text = valid_record().replace("- Migration boundary reviewed: Yes", "- Migration boundary reviewed: No")
    assert "rollback-incomplete" in codes(text)
