import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_production_acceptance.py"
SPEC = spec_from_file_location("validate_production_acceptance", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
validate_record = MODULE.validate_record


def valid_record(*, decision="GO", critical="0", high="0"):
    gates = [
        "Staging GO",
        "Backend CI",
        "Frontend CI",
        "Security Gate",
        "Deployment Validation",
        "Production preflight",
        "Backend production deploy",
        "Frontend production deploy",
        "Authenticated API smoke",
        "Frontend HTTPS smoke",
    ]
    operations = [
        "Kubernetes production environment",
        "PostgreSQL connectivity and encryption",
        "DNS and valid HTTPS",
        "Registry image-pull access",
        "Resource requests and limits",
        "Capacity or autoscaling controls",
        "Backup retention",
        "Restore exercise",
        "Centralized logs",
        "Availability, error, latency, and database alerts",
        "OpenAI usage and budget alerts",
        "Production admin and acceptance accounts",
        "Least-privilege access review",
    ]
    journeys = [
        "Controlled registration or invitation",
        "Sign in and sign out",
        "Session and persisted-state recovery",
        "Dashboard",
        "Create private investigation",
        "Add claims and evidence",
        "Record validation judgment",
        "View education-gap recommendations",
        "Mentor healthy response",
        "Mentor unavailable/fallback behavior",
        "Education lesson and adaptive assessment",
        "Owner isolation",
        "Answer-key privacy",
        "Support request path",
        "Account deletion and retention workflow",
    ]
    lines = [
        "# Production acceptance",
        "- Release SHA: " + "a" * 40,
        "- Rollback SHA: " + "b" * 40,
        "- Staging GO evidence: issue-29-go",
        "- Backend deploy workflow run: 20001",
        "- Frontend deploy workflow run: 20002",
        "- Production API URL: https://api.example.test",
        "- Production web URL: https://app.example.test",
        "- Release owner: Release Owner",
        "- Approval owner: Approval Owner",
        "- Release date/time (UTC): 2026-07-20T20:00:00Z",
        "- Backend image digest: sha256:" + "c" * 64,
        "- Running backend digest verified: Yes",
        "- Frontend image digest: sha256:" + "d" * 64,
        "- Running frontend digest verified: Yes",
        "- Migration revision before deploy: rev-before",
        "- Migration revision after deploy: rev-after",
        "| Gate | Result | Evidence | Notes |",
        "|---|---|---|---|",
    ]
    lines.extend(f"| {name} | Passed | ref | |" for name in gates)
    lines.extend(["| Check | Result | Owner | Notes |", "|---|---|---|---|"])
    lines.extend(f"| {name} | Passed | owner | |" for name in operations)
    lines.extend(["| Journey | Result | Evidence | Notes |", "|---|---|---|---|"])
    lines.extend(f"| {name} | Passed | ref | |" for name in journeys)
    lines.extend(
        [
            "- Previous backend and frontend images identified: Yes",
            "- Migration boundary reviewed: Yes",
            "- Backend rollback executed: Yes",
            "- Frontend rollback executed: Yes",
            "- Service health restored: Yes",
            "- Forward redeploy completed: Yes",
            f"- Decision: {decision}",
            "- Decision owner: Release Owner",
            "- Decision timestamp (UTC): 2026-07-20T21:00:00Z",
            f"- Unresolved critical defects: {critical}",
            f"- Unresolved high-severity defects: {high}",
            "> I verified that this decision is based on the exact release and rollback SHAs and backend and frontend image digests recorded above.",
        ]
    )
    return "\n".join(lines)


def codes(text):
    return {finding.code for finding in validate_record(text)}


def test_valid_go_record_passes():
    assert validate_record(valid_record()) == []


def test_release_and_rollback_must_be_distinct_valid_shas():
    text = valid_record().replace("- Rollback SHA: " + "b" * 40, "- Rollback SHA: " + "a" * 40)
    assert "invalid-rollback" in codes(text)


def test_invalid_or_unverified_image_digest_fails():
    text = valid_record().replace("sha256:" + "c" * 64, "latest", 1).replace(
        "- Running backend digest verified: Yes",
        "- Running backend digest verified: No",
    )
    assert {"invalid-image-digest", "image-provenance-unverified"}.issubset(codes(text))


def test_non_https_production_url_fails():
    text = valid_record().replace("https://api.example.test", "http://api.example.test")
    assert "invalid-url" in codes(text)


def test_pending_operational_gate_fails():
    text = valid_record().replace(
        "| Restore exercise | Passed |",
        "| Restore exercise | Pending |",
    )
    assert "incomplete-check" in codes(text)


def test_go_rejects_unresolved_critical_or_high_defects():
    findings = validate_record(valid_record(critical="1", high="ISSUE-401"))
    assert [finding.code for finding in findings].count("blocking-defect") == 2


def test_no_go_allows_documented_blocking_defects():
    assert validate_record(valid_record(decision="NO-GO", critical="1", high="ISSUE-401")) == []


def test_incomplete_rollback_is_rejected():
    text = valid_record().replace("- Backend rollback executed: Yes", "- Backend rollback executed: No")
    assert "rollback-incomplete" in codes(text)


def test_missing_privacy_journey_is_rejected():
    text = valid_record().replace(
        "| Answer-key privacy | Passed |",
        "| Portfolio execution | Passed |",
    )
    assert "missing-row" in codes(text)
