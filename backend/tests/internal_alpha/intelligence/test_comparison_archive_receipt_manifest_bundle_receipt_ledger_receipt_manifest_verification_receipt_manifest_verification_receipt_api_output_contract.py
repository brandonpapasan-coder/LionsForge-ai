import pytest

from app.api.routes import (
    internal_alpha_comparison_archive_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipts as routes,
)


@pytest.mark.parametrize(
    "malformed_findings",
    [
        None,
        (),
        "finding",
        ["valid finding", 1],
        [True],
    ],
)
def test_validate_route_fails_closed_for_malformed_validator_output(
    monkeypatch,
    malformed_findings: object,
) -> None:
    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda receipt, manifest: malformed_findings,
    )
    payload = routes.IntelligenceComparisonArchiveVerificationReceiptManifestVerificationReceiptValidationInput.model_validate(
        {"receipt": {}, "manifest": {}}
    )

    result = routes.validate_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
        payload,
        current_user=object(),  # type: ignore[arg-type]
    )

    assert result["valid"] is False
    assert result["findings"] == ["verification receipt manifest validation failed"]


def test_validate_route_preserves_exact_string_list_output(monkeypatch) -> None:
    findings = ["first finding", "second finding"]
    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda receipt, manifest: findings,
    )
    payload = routes.IntelligenceComparisonArchiveVerificationReceiptManifestVerificationReceiptValidationInput.model_validate(
        {"receipt": {}, "manifest": {}}
    )

    result = routes.validate_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
        payload,
        current_user=object(),  # type: ignore[arg-type]
    )

    assert result["valid"] is False
    assert result["findings"] == findings
