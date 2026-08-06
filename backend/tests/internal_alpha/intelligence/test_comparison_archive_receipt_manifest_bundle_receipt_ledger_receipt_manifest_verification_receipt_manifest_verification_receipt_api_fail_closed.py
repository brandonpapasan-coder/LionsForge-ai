import pytest

from app.api.routes import (
    internal_alpha_comparison_archive_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipts as routes,
)


@pytest.mark.parametrize("error_type", [TypeError, ValueError])
def test_validate_route_fails_closed_without_leaking_expected_errors(
    monkeypatch,
    error_type: type[Exception],
) -> None:
    def fake_validate(receipt: dict[str, object], manifest: dict[str, object]) -> list[str]:
        raise error_type("privacy-safe internal validation detail must not leak")

    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        fake_validate,
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
    assert "privacy-safe" not in str(result)


def test_validate_route_does_not_mask_unexpected_programming_errors(monkeypatch) -> None:
    def fake_validate(receipt: dict[str, object], manifest: dict[str, object]) -> list[str]:
        raise RuntimeError("unexpected validator defect")

    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        fake_validate,
    )
    payload = routes.IntelligenceComparisonArchiveVerificationReceiptManifestVerificationReceiptValidationInput.model_validate(
        {"receipt": {}, "manifest": {}}
    )

    with pytest.raises(RuntimeError, match="unexpected validator defect"):
        routes.validate_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
            payload,
            current_user=object(),  # type: ignore[arg-type]
        )
