from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_controlled_beta_acceptance.py"
spec = importlib.util.spec_from_file_location("validate_controlled_beta_acceptance", SCRIPT)
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = validator
spec.loader.exec_module(validator)


def complete_record(decision: str = "GO") -> str:
    selected = {
        "GO": "- [x] GO — all exit criteria are satisfied.",
        "CONDITIONAL GO": "- [x] CONDITIONAL GO — only explicitly time-bound, non-critical conditions remain.",
        "NO-GO": "- [x] NO-GO — one or more launch-critical criteria are not satisfied.",
    }
    conditions = "None" if decision != "CONDITIONAL GO" else "Resolve latency follow-up by 2026-08-01; owner: Operations."
    severity_2 = "0"
    return f"""# Controlled Beta Acceptance Record

## Release identity

- Release SHA: {'a' * 40}
- Previous rollback SHA: {'b' * 40}
- Backend image digest: sha256:{'c' * 64}
- Frontend image digest: sha256:{'d' * 64}
- Deployment date/time: 2026-07-26T16:00:00Z
- Operator: beta-operator
- Environment: controlled-production

## Approval and limits

- Maximum invited users: 100
- Accepted users: 80
- Per-user daily AI request limit: 25
- Aggregate daily AI budget: $500
- Abuse threshold: 10 rejected requests per hour
- Support owner: support-owner
- Incident owner: incident-owner
- Legal approver: legal-owner
- Security approver: security-owner
- Operations approver: operations-owner
- Product approver: product-owner

## Entry-gate evidence

- [x] Staging acceptance approved
- [x] Production readiness approved
- [x] Public policies and support processes live
- [x] Backup and restore evidence current
- [x] Rollback evidence current
- [x] Monitoring and alerts verified
- [x] No unresolved severity-1 or severity-2 defects
- [x] Invitation or registration cap enforced
- [x] Usage and budget limits enforced

Evidence links or identifiers:
release-evidence-001

## Critical journeys

| Journey | Result | Evidence | Defect reference |
| --- | --- | --- | --- |
| Invitation/approved registration | Passed | journey-01 | None |
| Authentication/session recovery | Passed | journey-02 | None |
| Investigation privacy and creation | Passed | journey-03 | None |
| Claims and evidence | Passed | journey-04 | None |
| Validation and provenance ledger | Passed | journey-05 | None |
| Education recommendations | Passed | journey-06 | None |
| Adaptive assessment | Passed | journey-07 | None |
| Mentor interaction | Passed | journey-08 | None |
| Support request | Passed | journey-09 | None |
| Privacy/deletion request intake | Passed | journey-10 | None |
| Logout/revoked access | Passed | journey-11 | None |

## Resilience exercises

| Exercise | Result | Evidence | Follow-up |
| --- | --- | --- | --- |
| AI provider timeout | Passed | exercise-01 | None |
| AI provider unavailable | Passed | exercise-02 | None |
| API outage alert | Passed | exercise-03 | None |
| Frontend outage alert | Passed | exercise-04 | None |
| Database failure alert | Passed | exercise-05 | None |
| Elevated error-rate alert | Passed | exercise-06 | None |
| Budget threshold alert | Passed | exercise-07 | None |
| Rollback | Passed | exercise-08 | None |
| Isolated restore verification | Passed | exercise-09 | None |

## Beta measurements

- Beta start: 2026-07-20T00:00:00Z
- Beta end: 2026-07-26T00:00:00Z
- Peak concurrent users: 42
- Availability: 99.95%
- API latency summary: p95 350 ms
- Frontend latency summary: p95 420 ms
- Error-rate summary: 0.2%
- AI requests: 1200
- AI cost total: $240
- AI cost per active user: $3
- Support reports: 4
- Severity-1 incidents: 0
- Severity-2 incidents: {severity_2}
- Other defects: 3

## Decision

- [ ] GO — all exit criteria are satisfied.
- [ ] CONDITIONAL GO — only explicitly time-bound, non-critical conditions remain.
- [ ] NO-GO — one or more launch-critical criteria are not satisfied.
{selected[decision]}

Decision rationale:
Evidence record is internally complete for the selected decision.

Conditions and deadlines:
{conditions}

- Legal approval: approved
- Security approval: approved
- Operations approval: approved
- Product approval: approved
- Owner approval: approved
- Decision date/time: 2026-07-26T16:30:00Z
"""


def messages(text: str) -> list[str]:
    return [finding.message for finding in validator.validate_record(text)]


def test_complete_go_record_is_valid():
    assert validator.validate_record(complete_record()) == []


def test_rejects_invalid_release_identity_and_equal_rollback():
    text = complete_record().replace("a" * 40, "not-a-sha").replace("b" * 40, "not-a-sha")
    assert sum(f.code == "invalid-sha" for f in validator.validate_record(text)) == 2

    same = complete_record().replace("b" * 40, "a" * 40)
    assert any(f.code == "invalid-rollback" for f in validator.validate_record(same))


def test_rejects_missing_gate_and_evidence():
    text = complete_record().replace("- [x] Monitoring and alerts verified", "- [ ] Monitoring and alerts verified")
    text = text.replace("| Mentor interaction | Passed | journey-08 | None |", "| Mentor interaction | Passed |  | None |")
    findings = validator.validate_record(text)
    assert any(f.code == "incomplete-gate" for f in findings)
    assert any(f.code == "missing-evidence" and "Mentor interaction" in f.message for f in findings)


def test_rejects_unsupported_result_and_missing_required_row():
    text = complete_record().replace("| AI provider timeout | Passed | exercise-01 | None |", "| AI provider timeout | Maybe | exercise-01 | None |")
    text = text.replace("| Logout/revoked access | Passed | journey-11 | None |\n", "")
    findings = validator.validate_record(text)
    assert any(f.code == "invalid-result" for f in findings)
    assert any(f.code == "missing-row" and "Logout/revoked access" in f.message for f in findings)


def test_rejects_invalid_counts_and_cap():
    text = complete_record().replace("- Accepted users: 80", "- Accepted users: 101")
    text = text.replace("- Other defects: 3", "- Other defects: -1")
    findings = validator.validate_record(text)
    assert any(f.code == "invalid-cap" for f in findings)
    assert any(f.code == "invalid-number" and "Other defects" in f.message for f in findings)


def test_go_rejects_failed_checks_incidents_and_conditions():
    text = complete_record().replace("| API outage alert | Passed | exercise-03 | None |", "| API outage alert | Failed | exercise-03 | defect-1 |")
    text = text.replace("- Severity-2 incidents: 0", "- Severity-2 incidents: 1")
    text = text.replace("Conditions and deadlines:\nNone", "Conditions and deadlines:\nFix incident by 2026-08-01")
    findings = validator.validate_record(text)
    assert sum(f.code == "decision-conflict" for f in findings) >= 3


def test_conditional_go_requires_conditions_and_no_blocking_results():
    valid = complete_record("CONDITIONAL GO")
    assert validator.validate_record(valid) == []

    invalid = valid.replace(
        "Resolve latency follow-up by 2026-08-01; owner: Operations.", "None"
    ).replace(
        "| API outage alert | Passed | exercise-03 | None |",
        "| API outage alert | Blocked | exercise-03 | incident-3 |",
    )
    findings = validator.validate_record(invalid)
    assert any(f.code == "missing-condition" for f in findings)
    assert any(f.code == "decision-conflict" for f in findings)


def test_rejects_multiple_decisions_and_private_content():
    text = complete_record().replace(
        "- [ ] NO-GO — one or more launch-critical criteria are not satisfied.",
        "- [x] NO-GO — one or more launch-critical criteria are not satisfied.",
    )
    text += "\n- API key: sk-private-value\n"
    findings = validator.validate_record(text)
    assert any(f.code == "invalid-decision" for f in findings)
    assert any(f.code == "private-content" for f in findings)


def test_cli_exit_behavior(tmp_path: Path):
    valid_path = tmp_path / "valid.md"
    valid_path.write_text(complete_record(), encoding="utf-8")
    valid = subprocess.run(
        [sys.executable, str(SCRIPT), str(valid_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert valid.returncode == 0
    assert "VALID:" in valid.stdout

    invalid_path = tmp_path / "invalid.md"
    invalid_path.write_text("# incomplete", encoding="utf-8")
    invalid = subprocess.run(
        [sys.executable, str(SCRIPT), str(invalid_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert invalid.returncode == 1
    assert "INVALID:" in invalid.stdout
