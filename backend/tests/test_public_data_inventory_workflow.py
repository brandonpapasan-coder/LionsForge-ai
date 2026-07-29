from pathlib import Path

WORKFLOW = (
    Path(__file__).resolve().parents[2]
    / ".github"
    / "workflows"
    / "public-data-inventory.yml"
)


def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_workflow_is_manual_read_only_and_exact_candidate_bound() -> None:
    text = workflow_text()
    assert "workflow_dispatch:" in text
    assert "pull_request:" not in text
    assert "push:" not in text
    assert "permissions:\n  contents: read" in text
    assert '[[ "${CANDIDATE_SHA}" =~ ^[0-9a-f]{40}$ ]]' in text
    assert "ref: ${{ inputs.candidate_sha }}" in text
    assert 'test "$(git rev-parse HEAD)" = "${CANDIDATE_SHA}"' in text
    assert 'git merge-base --is-ancestor "${CANDIDATE_SHA}" origin/main' in text


def test_workflow_rejects_unsafe_paths_and_retains_non_secret_report() -> None:
    text = workflow_text()
    assert '[[ "${INVENTORY_PATH}" != /* ]]' in text
    assert '[[ "${INVENTORY_PATH}" != *".."* ]]' in text
    assert 'test ! -L "${INVENTORY_PATH}"' in text
    assert "validate_public_data_inventory.py" in text
    assert "--expected-candidate" in text
    assert "public-data-inventory-report.json" in text
    assert "retention-days: 90" in text
    assert "does not provide legal approval" in text
    assert "authorize deployment, registration, controlled beta, payments, production billing, or general availability" in text
