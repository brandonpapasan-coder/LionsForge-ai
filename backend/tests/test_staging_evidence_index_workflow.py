from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "staging-evidence-index.yml"


def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_requires_exact_candidate_and_main_ancestry() -> None:
    text = workflow_text()
    assert "candidate_sha:" in text
    assert '[[ "${CANDIDATE_SHA}" =~ ^[0-9a-f]{40}$ ]]' in text
    assert "ref: ${{ inputs.candidate_sha }}" in text
    assert 'test "${actual_sha}" = "${CANDIDATE_SHA}"' in text
    assert "git fetch --no-tags origin main" in text
    assert 'git merge-base --is-ancestor "${CANDIDATE_SHA}" origin/main' in text


def test_builds_input_from_operator_entries() -> None:
    text = workflow_text()
    assert "entries_json:" in text
    assert 'entries = json.loads(os.environ["ENTRIES_JSON"])' in text
    assert '"candidate_sha": os.environ["CANDIDATE_SHA"]' in text
    assert '"selection_rationale": os.environ["SELECTION_RATIONALE"]' in text
    assert '"generated_at": datetime.now(timezone.utc)' in text
    assert '"entries": entries' in text


def test_generates_and_validates_before_enforcement() -> None:
    text = workflow_text()
    assert "manage_staging_evidence_index.py generate" in text
    assert "manage_staging_evidence_index.py validate" in text
    assert 'print(payload["index"]["readiness"])' in text
    assert text.index("Generate and validate evidence index") < text.index("Upload staging evidence index")
    assert text.index("Upload staging evidence index") < text.index("Enforce staging evidence READY")


def test_retains_ready_and_not_ready_indexes() -> None:
    text = workflow_text()
    assert "set +e" in text
    assert "generation_status=$?" in text
    assert "name: staging-evidence-index-${{ inputs.candidate_sha }}" in text
    assert "path: staging-evidence-index.json" in text
    assert "if-no-files-found: error" in text
    assert "retention-days: 90" in text


def test_summary_exposes_artifact_identity_and_guardrail() -> None:
    text = workflow_text()
    assert "Artifact ID" in text
    assert "Artifact digest" in text
    assert "Artifact URL" in text
    assert "does not independently prove live staging or authorize launch" in text
    assert '${{ steps.upload_index.outputs.artifact-id }}' in text
    assert '${{ steps.upload_index.outputs.artifact-url }}' in text
    assert '${{ steps.upload_index.outputs.artifact-digest }}' in text


def test_final_step_fails_closed_unless_ready() -> None:
    text = workflow_text()
    assert 'test "${GENERATION_STATUS}" = "0"' in text
    assert 'test "${READINESS}" = "READY"' in text
    assert "staging evidence index generation recorded NOT-READY" in text
    assert "staging evidence index did not record READY" in text
