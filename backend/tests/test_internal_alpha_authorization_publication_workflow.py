from pathlib import Path


WORKFLOW = (
    Path(__file__).resolve().parents[2] / ".github" / "workflows" / "internal-alpha-authorize.yml"
)


def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_publication_generation_and_verification_are_always_run_in_order():
    text = workflow_text()
    contract_verifier = text.index("manage_internal_alpha_artifact_contract.py verify")
    publication_writer = text.index("manage_internal_alpha_authorization_publication.py write")
    publication_verifier = text.index("manage_internal_alpha_authorization_publication.py verify")
    upload = text.index("id: evidence-upload")
    upload_receipt_writer = text.index(
        "manage_internal_alpha_authorization_upload_receipt.py write"
    )
    summary = text.index("Publish authorization summary")

    assert (
        contract_verifier
        < publication_writer
        < publication_verifier
        < upload
        < upload_receipt_writer
        < summary
    )
    assert (
        "Generate authorization publication record\n        id: publication\n        if: always()" in text
    )
    assert (
        "Verify authorization publication record\n"
        "        id: publication-verification\n"
        "        if: always()" in text
    )


def test_publication_record_binds_retained_artifact_identity():
    text = workflow_text()
    assert "--decision internal-alpha-authorization-decision.json" in text
    assert "--contract internal-alpha-authorization-artifact-contract.json" in text
    assert "--artifact-name internal-alpha-authorization-evidence" in text
    assert "--output internal-alpha-authorization-publication.json" in text


def test_publication_outcomes_are_fail_closed_in_summary():
    text = workflow_text()
    assert "PUBLICATION_OUTCOME: ${{ steps.publication.outcome }}" in text
    assert (
        "PUBLICATION_VERIFICATION_OUTCOME: "
        "${{ steps.publication-verification.outcome }}" in text
    )
    assert "Publication record generation outcome" in text
    assert "Publication record verification outcome" in text
    assert 'grep -q \'"authorized": true\' internal-alpha-authorization-upload-receipt.json' in text
    assert 'authorization="not-authorized"' in text


def test_publication_artifacts_are_retained_for_ninety_days():
    text = workflow_text()
    upload = text.index("actions/upload-artifact@v4")
    for path in (
        "internal-alpha-authorization-publication.json",
        "internal-alpha-authorization-publication-generation.txt",
        "internal-alpha-authorization-publication-verification.txt",
    ):
        assert text.index(path, upload) > upload
    assert "if-no-files-found: error" in text
    assert "retention-days: 90" in text


def test_publication_summary_preserves_repository_only_boundary():
    text = workflow_text()
    assert "validates repository provenance only" in text
    assert "does not independently prove external staging behavior" in text
    assert "authorize public access" in text
