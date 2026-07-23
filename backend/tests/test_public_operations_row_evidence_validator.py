import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[2] / "scripts" / "validate_public_operations_row_evidence.py"
)
SPEC = spec_from_file_location("validate_public_operations_row_evidence", SCRIPT)
assert SPEC and SPEC.loader
MODULE = module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
validate_record = MODULE.validate_record


def valid_record() -> str:
    policies = [
        "Privacy Notice",
        "Terms of Service",
        "Responsible AI disclosure",
        "Data retention and deletion policy",
        "Acceptable use and abuse reporting",
    ]
    channels = [
        "General support",
        "Privacy requests",
        "Security reports",
        "Abuse reports",
    ]
    workflows = [
        "Privacy request intake",
        "Identity verification",
        "Account closure and authentication disablement",
        "Eligible data deletion or de-identification",
        "Backup-expiry handling",
        "General support intake and response",
        "Abuse report intake and escalation",
        "Security report intake and escalation",
        "Consent recording and policy-version capture",
    ]
    approvals = [
        "Business owner",
        "Legal reviewer",
        "Privacy owner",
        "Security owner",
        "Support operations owner",
        "Release owner",
    ]

    lines = [
        "- Review date: 2026-07-20",
        "- Intended effective date: 2026-08-01",
        "| Surface | Version or SHA | Effective date | Business approver role | "
        "Legal approver role | Status |",
        "|---|---|---|---|---|---|",
    ]
    lines.extend(
        f"| {name} | v1 | 2026-08-01 | Business Owner | Legal Reviewer | APPROVED |"
        for name in policies
    )
    lines.extend(
        [
            "| Function | Public channel | Operational owner role | "
            "Monitoring verified | Test evidence reference |",
            "|---|---|---|---|---|",
        ]
    )
    lines.extend(
        f"| {name} | public@example.test | Operations Owner | VERIFIED | evidence-{index} |"
        for index, name in enumerate(channels, start=1)
    )
    lines.extend(
        [
            "| Workflow | Test date | Tester role | Evidence reference | Result |",
            "|---|---|---|---|---|",
        ]
    )
    lines.extend(
        f"| {name} | 2026-07-20 | Tester | evidence-{index} | PASSED |"
        for index, name in enumerate(workflows, start=1)
    )
    lines.extend(
        [
            "| Approval | Approver role | Date | Status |",
            "|---|---|---|---|",
        ]
    )
    lines.extend(f"| {name} | {name} | 2026-07-20 | APPROVED |" for name in approvals)
    return "\n".join(lines)


def codes(text: str) -> set[str]:
    return {finding.code for finding in validate_record(text)}


def test_valid_row_evidence_passes() -> None:
    assert validate_record(valid_record()) == []


def test_policy_effective_after_launch_fails() -> None:
    text = valid_record().replace(
        "| Privacy Notice | v1 | 2026-08-01 |",
        "| Privacy Notice | v1 | 2026-08-02 |",
    )
    assert "policy-effective-after-launch" in codes(text)


def test_placeholder_channel_evidence_fails() -> None:
    text = valid_record().replace("evidence-1", "TODO", 1)
    assert "invalid-row-reference" in codes(text)


def test_workflow_test_after_review_fails() -> None:
    text = valid_record().replace(
        "| Privacy request intake | 2026-07-20 |",
        "| Privacy request intake | 2026-07-21 |",
    )
    assert "workflow-tested-after-review" in codes(text)


def test_invalid_workflow_date_fails() -> None:
    text = valid_record().replace(
        "| Identity verification | 2026-07-20 |",
        "| Identity verification | July 20, 2026 |",
    )
    assert "invalid-row-date" in codes(text)


def test_approval_after_review_fails() -> None:
    text = valid_record().replace(
        "| Legal reviewer | Legal reviewer | 2026-07-20 |",
        "| Legal reviewer | Legal reviewer | 2026-07-21 |",
    )
    assert "approval-after-review" in codes(text)
