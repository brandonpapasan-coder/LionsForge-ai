from pathlib import Path


WORKFLOW = (
    Path(__file__).resolve().parents[2] / ".github" / "workflows" / "internal-alpha-authorize.yml"
)


def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_workflow_is_manual_and_read_only():
    text = workflow_text()
    assert "workflow_dispatch:" in text
    assert "contents: read" in text
    assert "actions: read" in text
    assert "id-token: write" not in text


def test_workflow_requires_protected_main_dispatch_and_checkout():
    text = workflow_text()
    assert "DISPATCH_REF: ${{ github.ref }}" in text
    assert '[[ "${DISPATCH_REF}" == "refs/heads/main" ]]' in text
    assert "ref: refs/heads/main" in text
    assert 'checked_out_sha="$(git rev-parse HEAD)"' in text
    assert 'protected_main_sha="$(git rev-parse origin/main)"' in text
    assert '[[ "${checked_out_sha}" == "${protected_main_sha}" ]]' in text


def test_workflow_sha_must_equal_protected_main():
    text = workflow_text()
    assert "WORKFLOW_SHA: ${{ github.workflow_sha }}" in text
    assert '[[ "${WORKFLOW_SHA}" =~ ^[0-9a-f]{40}$ ]]' in text
    assert '[[ "${WORKFLOW_SHA}" == "${protected_main_sha}" ]]' in text
    assert "Workflow definition SHA does not equal protected main" in text


def test_workflow_requires_exact_sha_and_image_digests():
    text = workflow_text()
    assert "candidate_sha:" in text
    assert "backend_digest:" in text
    assert "frontend_digest:" in text
    assert "^[0-9a-f]{40}$" in text
    assert "^sha256:[0-9a-f]{64}$" in text


def test_workflow_binds_inputs_to_canonical_go_record():
    text = workflow_text()
    assert "docs/operations/internal-alpha-readiness-gate.md" in text
    assert '[[ "${decision}" == "GO" ]]' in text
    assert '[[ "${recorded_sha}" == "${CANDIDATE_SHA}" ]]' in text
    assert '[[ "${recorded_backend}" == "${BACKEND_DIGEST}" ]]' in text
    assert '[[ "${recorded_frontend}" == "${FRONTEND_DIGEST}" ]]' in text


def test_workflow_requires_main_ancestry_and_release_gates():
    text = workflow_text()
    assert 'git cat-file -e "${CANDIDATE_SHA}^{commit}"' in text
    assert 'git merge-base --is-ancestor "${CANDIDATE_SHA}" origin/main' in text
    assert "python scripts/verify_release_gates.py" in text
    assert '--sha "${RELEASE_SHA}"' in text


def test_workflow_generates_and_retains_authorization_manifest():
    text = workflow_text()
    assert "python scripts/write_internal_alpha_authorization_manifest.py" in text
    assert '--dispatch-ref "${DISPATCH_REF}"' in text
    assert '--workflow-sha "${WORKFLOW_SHA}"' in text
    assert '--protected-main-sha "${PROTECTED_MAIN_SHA}"' in text
    assert "internal-alpha-authorization-manifest.json" in text
    assert "internal-alpha-authorization-manifest.txt" in text
    assert "MANIFEST_OUTCOME: ${{ steps.manifest.outcome }}" in text
    assert "Authorization manifest outcome" in text


def test_workflow_validates_and_retains_traceable_evidence():
    text = workflow_text()
    assert "python scripts/validate_internal_alpha_readiness.py" in text
    assert "python scripts/validate_internal_alpha_evidence.py" in text
    assert "internal-alpha-evidence-validation.txt" in text
    assert "EVIDENCE_OUTCOME: ${{ steps.evidence.outcome }}" in text
    assert "Evidence validator outcome" in text
    assert "GITHUB_STEP_SUMMARY" in text
    assert "internal-alpha-authorization-evidence" in text
    assert "retention-days: 90" in text
