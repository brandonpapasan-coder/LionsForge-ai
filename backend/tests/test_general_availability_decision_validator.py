from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate_general_availability_decision.py"
spec = importlib.util.spec_from_file_location("validate_general_availability_decision", SCRIPT)
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = validator
spec.loader.exec_module(validator)


def complete_record(decision: str = "GO") -> str:
    selected = {
        "GO": "- [x] GO — all mandatory GA exit criteria are satisfied for the exact release candidate.",
        "NO-GO": "- [x] NO-GO — one or more launch-critical criteria are not satisfied.",
    }
    blocker = "None" if decision == "GO" else "Production acceptance evidence is incomplete."
    blocker_owner = "None" if decision == "GO" else "operations-owner"
    return f"""# General Availability Decision Record

## Release identity

- Release SHA: {'a' * 40}
- Previous rollback SHA: {'b' * 40}
- Backend image digest: sha256:{'c' * 64}
- Frontend image digest: sha256:{'d' * 64}
- Deployment environment: production
- Proposed GA date/time (UTC): 2026-08-01T14:00:00Z
- Release owner: release-owner
- Operations owner: operations-owner

## Upstream acceptance evidence

- Production acceptance evidence: production-record-001
- Public-operations activation evidence: public-ops-record-001
- Controlled-beta acceptance evidence: beta-record-001
- Candidate ancestry evidence: ancestry-run-001
- Running backend digest evidence: backend-digest-run-001
- Running frontend digest evidence: frontend-digest-run-001

## Launch controls

- Registration mode: controlled-public
- Maximum registered users: 1000
- Per-user daily AI request limit: 50
- Aggregate daily AI budget (USD): $1500.00
- Abuse threshold: 20 rejected requests per hour
- Support owner: support-owner
- Incident owner: incident-owner
- Privacy owner: privacy-owner
- Security owner: security-owner
- Rollback authority: operations-owner

## Critical exit gates

- [x] Production acceptance is approved for this exact release and image digests
- [x] Public policies, consent, deletion, retention, support, abuse, and security-reporting workflows are live
- [x] Controlled beta completed on this exact release candidate or an explicitly validated successor
- [x] Running backend and frontend image digests match the approved immutable digests
- [x] Backup and isolated restore evidence is current
- [x] Rollback evidence is current
- [x] Monitoring and launch-critical alerts are verified
- [x] Registration, usage, abuse, and budget limits are enforced
- [x] Support and incident owners are on duty
- [x] No unresolved severity-1 or severity-2 incidents remain
- [x] No unresolved critical or high-severity defects remain
- [x] No expired exception remains open

Evidence links or identifiers:
ga-evidence-index-001

## Operational evidence

| Control | Result | Evidence | Owner / follow-up |
| --- | --- | --- | --- |
| HTTPS API and web availability | Passed | control-01 | None |
| Authentication and session recovery | Passed | control-02 | None |
| Owner isolation and privacy | Passed | control-03 | None |
| Investigation, claims, and evidence workflow | Passed | control-04 | None |
| Validation and provenance workflow | Passed | control-05 | None |
| Education and adaptive assessment | Passed | control-06 | None |
| Mentor provider-failure behavior | Passed | control-07 | None |
| Account deletion and retention workflow | Passed | control-08 | None |
| Support and abuse-reporting workflow | Passed | control-09 | None |
| Security-reporting workflow | Passed | control-10 | None |
| Monitoring and alert delivery | Passed | control-11 | None |
| Rollback exercise | Passed | control-12 | None |
| Isolated restore verification | Passed | control-13 | None |
| Budget-threshold enforcement | Passed | control-14 | None |

## Controlled-beta and launch measurements

- Beta active users: 400
- Peak concurrent users: 75
- Availability: 99.95%
- API latency summary: p95 320 ms
- Frontend latency summary: p95 410 ms
- Error-rate summary: 0.15%
- AI requests: 12000
- AI cost total (USD): $900.00
- AI cost per active user (USD): $2.25
- Support reports: 15
- Severity-1 incidents: 0
- Severity-2 incidents: 0
- Unresolved critical defects: 0
- Unresolved high-severity defects: 0
- Other unresolved defects: 3
- Open exceptions: 0
- Expired exceptions: 0

## Risks, exceptions, and blockers

- Open-risk summary: No launch-critical open risks.
- Exception register evidence: exception-register-001
- Blocker rationale: {blocker}
- Blocker owner: {blocker_owner}

## Approvals

- Legal approval: approved
- Privacy approval: approved
- Security approval: approved
- Operations approval: approved
- Support approval: approved
- Product approval: approved
- Executive owner approval: approved

## Decision

- [ ] GO — all mandatory GA exit criteria are satisfied for the exact release candidate.
- [ ] NO-GO — one or more launch-critical criteria are not satisfied.
{selected[decision]}

Decision rationale:
The record is internally complete for the selected decision.

- Decision owner: executive-owner
- Decision date/time (UTC): 2026-07-31T18:00:00Z
"""


def test_complete_go_record_is_valid():
    assert validator.validate_record(complete_record()) == []


def test_complete_no_go_record_is_valid():
    assert validator.validate_record(complete_record("NO-GO")) == []


def test_rejects_invalid_release_identity_and_equal_rollback():
    invalid = complete_record().replace("a" * 40, "invalid-sha").replace("b" * 40, "invalid-sha")
    assert sum(f.code == "invalid-sha" for f in validator.validate_record(invalid)) == 2
    same = complete_record().replace("b" * 40, "a" * 40)
    assert any(f.code == "invalid-rollback" for f in validator.validate_record(same))


def test_rejects_unchecked_gate_and_missing_control_evidence():
    text = complete_record().replace(
        "- [x] Monitoring and launch-critical alerts are verified",
        "- [ ] Monitoring and launch-critical alerts are verified",
    ).replace(
        "| Rollback exercise | Passed | control-12 | None |",
        "| Rollback exercise | Passed |  | None |",
    )
    findings = validator.validate_record(text)
    assert any(f.code == "incomplete-gate" for f in findings)
    assert any(f.code == "missing-evidence" and "Rollback exercise" in f.message for f in findings)


def test_rejects_missing_control_and_unsupported_result():
    text = complete_record().replace(
        "| Security-reporting workflow | Passed | control-10 | None |\n", ""
    ).replace(
        "| Budget-threshold enforcement | Passed | control-14 | None |",
        "| Budget-threshold enforcement | Maybe | control-14 | None |",
    )
    findings = validator.validate_record(text)
    assert any(f.code == "missing-row" and "Security-reporting" in f.message for f in findings)
    assert any(f.code == "invalid-result" for f in findings)


def test_rejects_invalid_counts_money_and_cap():
    text = complete_record().replace("- Beta active users: 400", "- Beta active users: 1001")
    text = text.replace("- Other unresolved defects: 3", "- Other unresolved defects: -1")
    text = text.replace("- AI cost total (USD): $900.00", "- AI cost total (USD): unknown")
    findings = validator.validate_record(text)
    assert any(f.code == "invalid-cap" for f in findings)
    assert any(f.code == "invalid-number" and "Other unresolved defects" in f.message for f in findings)
    assert any(f.code == "invalid-money" for f in findings)


def test_go_rejects_incidents_defects_expired_exceptions_and_failed_controls():
    text = complete_record().replace("- Severity-2 incidents: 0", "- Severity-2 incidents: 1")
    text = text.replace("- Unresolved high-severity defects: 0", "- Unresolved high-severity defects: 2")
    text = text.replace("- Expired exceptions: 0", "- Expired exceptions: 1")
    text = text.replace(
        "| HTTPS API and web availability | Passed | control-01 | None |",
        "| HTTPS API and web availability | Failed | control-01 | incident-01 |",
    )
    findings = validator.validate_record(text)
    assert sum(f.code == "decision-conflict" for f in findings) >= 4


def test_no_go_requires_blocker_rationale_and_owner():
    text = complete_record("NO-GO").replace(
        "- Blocker rationale: Production acceptance evidence is incomplete.", "- Blocker rationale:"
    ).replace("- Blocker owner: operations-owner", "- Blocker owner:")
    findings = validator.validate_record(text)
    assert sum(f.code == "missing-blocker" for f in findings) == 2


def test_rejects_multiple_decisions_and_private_content():
    text = complete_record().replace(
        "- [ ] NO-GO — one or more launch-critical criteria are not satisfied.",
        "- [x] NO-GO — one or more launch-critical criteria are not satisfied.",
    )
    text += "\n- API key: sk-private-example\n"
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
