from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "staging-acceptance-record.yml"


def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_workflow_requires_exact_protected_main_candidate() -> None:
    text = workflow_text()
    assert "candidate_sha:" in text
    assert '[[ "${CANDIDATE_SHA}" =~ ^[0-9a-f]{40}$ ]]' in text
    assert "ref: ${{ inputs.candidate_sha }}" in text
    assert 'test "${actual_sha}" = "${CANDIDATE_SHA}"' in text
    assert "git fetch --no-tags origin main" in text
    assert 'git merge-base --is-ancestor "${CANDIDATE_SHA}" origin/main' in text


def test_workflow_builds_input_from_supplied_evidence_json() -> None:
    text = workflow_text()
    assert "selection_rationale:" in text
    assert "evidence_json:" in text
    assert 'evidence = json.loads(os.environ["EVIDENCE_JSON"])' in text
    assert '"candidate_sha": os.environ["CANDIDATE_SHA"]' in text
    assert '"selection_rationale": os.environ["SELECTION_RATIONALE"]' in text
    assert '"generated_at": datetime.now(timezone.utc)' in text
    assert '"evidence": evidence' in text


def test_workflow_generates_validates_and_retains_record_before_go_enforcement() -> None:
    text = workflow_text()
    assert "manage_staging_acceptance_record.py generate" in text
    assert "--output staging-acceptance-record.json" in text
    assert "manage_staging_acceptance_record.py validate" in text
    assert "id: upload_acceptance" in text
    assert "name: staging-acceptance-record-${{ inputs.candidate_sha }}" in text
    assert "path: staging-acceptance-record.json" in text
    assert "retention-days: 90" in text
    assert text.index("Upload staging acceptance record") < text.index("Enforce staging acceptance GO")


def test_workflow_preserves_no_go_record_and_fails_closed() -> None:
    text = workflow_text()
    assert "set +e" in text
    assert "generation_status=$?" in text
    assert 'echo "generation_status=${generation_status}" >> "${GITHUB_OUTPUT}"' in text
    assert 'test "${GENERATION_STATUS}" = "0"' in text
    assert "staging acceptance generation recorded NO-GO" in text
    assert 'test "${DECISION}" = "GO"' in text
    assert "staging acceptance record did not record GO" in text


def test_workflow_summary_exposes_artifact_identity_and_guardrail() -> None:
    text = workflow_text()
    assert "${{ steps.upload_acceptance.outputs.artifact-id }}" in text
    assert "${{ steps.upload_acceptance.outputs.artifact-url }}" in text
    assert "${{ steps.upload_acceptance.outputs.artifact-digest }}" in text
    assert "This record summarizes supplied evidence only" in text
    assert '>> "${GITHUB_STEP_SUMMARY}"' in text
