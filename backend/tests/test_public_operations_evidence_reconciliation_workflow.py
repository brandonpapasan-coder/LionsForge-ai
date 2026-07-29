from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "public-operations-evidence-reconciliation.yml"


def text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_workflow_is_manual_read_only_and_candidate_bound() -> None:
    value = text()
    assert "workflow_dispatch:" in value
    assert "pull_request:" not in value and "push:" not in value
    assert "permissions:\n  contents: read" in value
    assert '[[ "${CANDIDATE_SHA}" =~ ^[0-9a-f]{40}$ ]]' in value
    assert "ref: ${{ inputs.candidate_sha }}" in value
    assert 'git merge-base --is-ancestor "${CANDIDATE_SHA}" origin/main' in value


def test_workflow_rejects_unsafe_paths_and_retains_report() -> None:
    value = text()
    assert '[[ "${RECORD_PATH}" != /* ]]' in value
    assert '[[ "${RECORD_PATH}" != *".."* ]]' in value
    assert 'test ! -L "${RECORD_PATH}"' in value
    assert "validate_public_operations_evidence_reconciliation.py" in value
    assert "--expected-candidate" in value
    assert "retention-days: 90" in value
    assert "does not activate deployment" in value
