from pathlib import Path


WORKFLOW = (
    Path(__file__).resolve().parents[2]
    / ".github"
    / "workflows"
    / "public-operations-activation-receipt.yml"
)


def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_workflow_requires_exact_candidate_and_safe_record_path() -> None:
    text = workflow_text()
    assert "candidate_sha:" in text
    assert "record_path:" in text
    assert '[[ "${CANDIDATE_SHA}" =~ ^[0-9a-f]{40}$ ]]' in text
    assert '[[ "${RECORD_PATH}" != /* ]]' in text
    assert '[[ "${RECORD_PATH}" != *".."* ]]' in text
    assert "ref: ${{ inputs.candidate_sha }}" in text
    assert 'test "$(git rev-parse HEAD)" = "${CANDIDATE_SHA}"' in text
    assert 'git merge-base --is-ancestor "${CANDIDATE_SHA}" origin/main' in text


def test_workflow_validates_source_before_receipting() -> None:
    text = workflow_text()
    source_validation = text.index("Validate source activation record")
    generation = text.index("Generate candidate-bound receipt")
    reverification = text.index("Reverify receipt against source and candidate")
    upload = text.index("Upload activation receipt")

    assert source_validation < generation < reverification < upload
    assert 'python scripts/validate_public_operations_activation.py "${RECORD_PATH}"' in text
    assert "manage_public_operations_activation_receipt.py generate" in text
    assert "manage_public_operations_activation_receipt.py validate" in text
    assert '--expected-candidate-sha "${CANDIDATE_SHA}"' in text


def test_workflow_retains_receipt_and_preserves_authorization_boundary() -> None:
    text = workflow_text()
    assert "actions/upload-artifact@v4" in text
    assert "retention-days: 90" in text
    assert "artifact-digest" in text
    assert "does not authorize registration, controlled beta, payments, or launch" in text
    assert "permissions:\n  contents: read" in text
