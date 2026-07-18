from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "staging-acceptance-validate.yml"


def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_workflow_is_manual_and_read_only():
    text = workflow_text()
    assert "workflow_dispatch:" in text
    assert "contents: read" in text
    assert "id-token: write" not in text


def test_workflow_requires_record_path_and_release_sha():
    text = workflow_text()
    assert "record_path:" in text
    assert "release_sha:" in text
    assert "^[0-9a-f]{40}$" in text
    assert 'git cat-file -e "${RELEASE_SHA}^{commit}"' in text
    assert 'git merge-base --is-ancestor "${RELEASE_SHA}" origin/main' in text


def test_workflow_restricts_path_and_matches_record_sha():
    text = workflow_text()
    assert '"${RECORD_PATH}" != docs/*.md' in text
    assert '"${workspace_path}"/docs/*.md' in text
    assert "Release candidate SHA:" in text
    assert '"${recorded_sha}" != "${RELEASE_SHA}"' in text


def test_workflow_runs_validator_and_writes_summary():
    text = workflow_text()
    assert 'python scripts/validate_staging_acceptance.py "${RECORD_PATH}"' in text
    assert "staging-acceptance-validation.txt" in text
    assert "GITHUB_STEP_SUMMARY" in text
