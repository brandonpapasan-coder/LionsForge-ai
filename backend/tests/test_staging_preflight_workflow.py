from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "staging-preflight.yml"


def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_staging_preflight_requires_exact_candidate_sha() -> None:
    text = workflow_text()
    assert "candidate_sha:" in text
    assert "required: true" in text
    assert '[[ "${CANDIDATE_SHA}" =~ ^[0-9a-f]{40}$ ]]' in text
    assert "ref: ${{ inputs.candidate_sha }}" in text
    assert 'test "${actual_sha}" = "${CANDIDATE_SHA}"' in text


def test_staging_preflight_rejects_non_main_candidate() -> None:
    text = workflow_text()
    assert "git fetch --no-tags origin main" in text
    assert 'git merge-base --is-ancestor "${CANDIDATE_SHA}" origin/main' in text
    assert "candidate_sha is not contained in origin/main" in text


def test_staging_preflight_retains_provenance_evidence() -> None:
    text = workflow_text()
    assert 'payload["schema_version"] = 1' in text
    assert '"candidate_sha": os.environ["CANDIDATE_SHA"]' in text
    assert '"repository": os.environ["REPOSITORY"]' in text
    assert '"workflow_run_id": int(os.environ["RUN_ID"])' in text
    assert '"workflow_run_attempt": int(os.environ["RUN_ATTEMPT"])' in text
    assert '"workflow_run_url": (' in text
    assert '"skip_endpoints": os.environ["SKIP_ENDPOINTS"].lower() == "true"' in text
    assert '"generated_at": datetime.now(timezone.utc)' in text
    assert "name: staging-preflight-${{ inputs.candidate_sha }}" in text
    assert "if-no-files-found: error" in text
    assert "retention-days: 90" in text


def test_staging_preflight_summary_exposes_evidence_identity() -> None:
    text = workflow_text()
    assert "id: upload_evidence" in text
    assert "${{ steps.upload_evidence.outputs.artifact-id }}" in text
    assert "${{ steps.upload_evidence.outputs.artifact-url }}" in text
    assert "${{ steps.upload_evidence.outcome }}" in text
    assert '>> "${GITHUB_STEP_SUMMARY}"' in text
