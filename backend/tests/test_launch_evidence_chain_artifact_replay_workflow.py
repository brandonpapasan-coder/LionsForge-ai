from pathlib import Path

WORKFLOW = (
    Path(__file__).resolve().parents[2]
    / ".github"
    / "workflows"
    / "launch-evidence-chain-artifact-replay.yml"
)


def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_workflow_is_manual_read_only_and_exact_candidate_bound() -> None:
    text = workflow_text()
    assert "workflow_dispatch:" in text
    assert "pull_request:" not in text
    assert "push:" not in text
    assert "actions: read" in text
    assert "contents: read" in text
    assert '[[ "${CANDIDATE_SHA}" =~ ^[0-9a-f]{40}$ ]]' in text
    assert "ref: ${{ inputs.candidate_sha }}" in text
    assert 'git merge-base --is-ancestor "${CANDIDATE_SHA}" origin/main' in text


def test_workflow_requires_successful_source_run_and_unique_unexpired_artifacts() -> None:
    text = workflow_text()
    assert 'test "$(jq -r \'.name\' <<<"${run_json}")" = "Launch Evidence Chain Receipt"' in text
    assert 'test "$(jq -r \'.conclusion\' <<<"${run_json}")" = "success"' in text
    assert ".expired == false" in text
    assert 'test "${primary_count}" = "1"' in text
    assert 'test "${provenance_count}" = "1"' in text
    assert "actions/artifacts/${PRIMARY_ID}/zip" in text
    assert "actions/artifacts/${PROVENANCE_ID}/zip" in text


def test_workflow_verifies_before_retaining_report_and_preserves_boundary() -> None:
    text = workflow_text()
    resolve = text.index("Resolve successful source run and exact artifacts")
    download = text.index("Download retained artifacts")
    verify = text.index("Independently verify retained artifact replay")
    upload = text.index("Upload replay report")
    assert resolve < download < verify < upload
    assert "verify_launch_evidence_chain_artifact_replay.py" in text
    assert "retention-days: 90" in text
    assert "does not authorize deployment, registration, controlled beta, payments, production billing, or general availability" in text
