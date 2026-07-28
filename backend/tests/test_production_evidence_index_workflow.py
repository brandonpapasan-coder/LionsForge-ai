from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "production-evidence-index.yml"


def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_requires_exact_production_and_staging_candidates() -> None:
    text = workflow_text()
    assert "candidate_sha:" in text
    assert "staging_candidate_sha:" in text
    assert '[[ "${CANDIDATE_SHA}" =~ ^[0-9a-f]{40}$ ]]' in text
    assert '[[ "${STAGING_CANDIDATE_SHA}" =~ ^[0-9a-f]{40}$ ]]' in text
    assert "ref: ${{ inputs.candidate_sha }}" in text
    assert 'test "${actual_sha}" = "${CANDIDATE_SHA}"' in text
    assert 'git merge-base --is-ancestor "${CANDIDATE_SHA}" origin/main' in text


def test_builds_lineage_bound_generation_input() -> None:
    text = workflow_text()
    assert '"candidate_sha": os.environ["CANDIDATE_SHA"]' in text
    assert '"staging_candidate_sha": os.environ["STAGING_CANDIDATE_SHA"]' in text
    assert '"entries": json.loads(os.environ["ENTRIES_JSON"])' in text
    assert '"generated_at": datetime.now(timezone.utc)' in text


def test_generates_validates_and_retains_before_enforcement() -> None:
    text = workflow_text()
    assert "manage_production_evidence_index.py generate" in text
    assert "manage_production_evidence_index.py validate" in text
    assert 'print(json.loads(Path("production-evidence-index.json").read_text(encoding="utf-8"))["index"]["decision"])' in text
    assert text.index("Generate and validate production evidence index") < text.index("Upload production evidence index")
    assert text.index("Upload production evidence index") < text.index("Enforce production evidence READY")
    assert "set +e" in text
    assert "generation_status=$?" in text
    assert "retention-days: 90" in text


def test_summary_exposes_identity_and_guardrail() -> None:
    text = workflow_text()
    assert "Production candidate" in text
    assert "Accepted staging candidate" in text
    assert "Artifact ID" in text
    assert "Artifact digest" in text
    assert "Artifact URL" in text
    assert "does not authorize public registration, beta, or launch" in text


def test_final_step_fails_closed_unless_ready() -> None:
    text = workflow_text()
    assert 'test "${GENERATION_STATUS}" = "0"' in text
    assert 'test "${DECISION}" = "READY"' in text
    assert "production evidence index generation recorded NOT-READY" in text
    assert "production evidence index did not record READY" in text
