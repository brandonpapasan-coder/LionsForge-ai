from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "internal-alpha-feedback.yml"


def text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_workflow_is_manual_read_only_and_candidate_bound() -> None:
    value = text()
    assert "workflow_dispatch:" in value
    assert "pull_request:" not in value and "push:" not in value
    assert "permissions:\n  contents: read" in value
    assert '[[ "${CANDIDATE_SHA}" =~ ^[0-9a-f]{40}$ ]]' in value
    assert "ref: ${{ inputs.candidate_sha }}" in value
    assert 'test "$(git rev-parse HEAD)" = "${CANDIDATE_SHA}"' in value
    assert 'git merge-base --is-ancestor "${CANDIDATE_SHA}" origin/main' in value


def test_workflow_preserves_private_internal_boundary() -> None:
    value = text()
    assert '[[ "${MANIFEST_PATH}" != /* ]]' in value
    assert '[[ "${MANIFEST_PATH}" != *".."* ]]' in value
    assert 'test ! -L "${MANIFEST_PATH}"' in value
    assert "validate_internal_alpha_feedback.py" in value
    assert "--expected-candidate" in value
    assert "retention-days: 90" in value
    assert "does not expose feedback publicly" in value
