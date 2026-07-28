from pathlib import Path


WORKFLOW = (
    Path(__file__).resolve().parents[2]
    / ".github"
    / "workflows"
    / "launch-evidence-chain-receipt.yml"
)


def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_workflow_requires_exact_candidate_and_safe_paths() -> None:
    text = workflow_text()
    assert '[[ "${CANDIDATE_SHA}" =~ ^[0-9a-f]{40}$ ]]' in text
    assert '[[ "${path}" != /* ]]' in text
    assert '[[ "${path}" != *".."* ]]' in text
    assert "ref: ${{ inputs.candidate_sha }}" in text
    assert 'test "$(git rev-parse HEAD)" = "${CANDIDATE_SHA}"' in text
    assert 'git merge-base --is-ancestor "${CANDIDATE_SHA}" origin/main' in text


def test_workflow_validates_chain_before_receipt_and_revalidates_before_upload() -> None:
    text = workflow_text()
    chain = text.index("Validate complete launch evidence chain")
    generate = text.index("Generate deterministic chain receipt")
    revalidate = text.index("Revalidate receipt against source records")
    upload = text.index("Upload chain receipt and summary")

    assert chain < generate < revalidate < upload
    assert "validate_launch_evidence_chain.py" in text
    assert "launch_evidence_chain_receipt.py generate" in text
    assert "launch_evidence_chain_receipt.py validate" in text


def test_workflow_retains_non_secret_artifacts_and_preserves_authorization_boundary() -> None:
    text = workflow_text()
    assert "actions/upload-artifact@v4" in text
    assert "retention-days: 90" in text
    assert "launch-evidence-chain-receipt.json" in text
    assert "launch-evidence-chain-validation.txt" in text
    assert "does not authorize deployment, registration, controlled beta, payments, production billing, or general availability" in text
    assert "permissions:\n  contents: read" in text
