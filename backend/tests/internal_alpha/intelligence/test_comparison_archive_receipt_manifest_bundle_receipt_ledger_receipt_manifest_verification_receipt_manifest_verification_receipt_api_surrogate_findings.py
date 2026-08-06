import pytest
from fastapi import HTTPException

from app.api.routes import (
    internal_alpha_comparison_archive_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipts as routes,
)


def _validation_payload():
    return routes.IntelligenceComparisonArchiveVerificationReceiptManifestVerificationReceiptValidationInput.model_validate(
        {"receipt": {}, "manifest": {}}
    )


def _create_payload():
    return routes.IntelligenceComparisonArchiveVerificationReceiptManifestVerificationReceiptInput.model_validate(
        {"manifest": {}}
    )


@pytest.mark.parametrize("finding", ["digest\ud800mismatch", "digest\udfffmismatch"])
def test_validate_route_replaces_surrogate_finding_with_generic_failure(
    monkeypatch, finding: str
) -> None:
    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda receipt, manifest: [finding],
    )

    result = routes.validate_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
        _validation_payload(), current_user=object()  # type: ignore[arg-type]
    )

    assert result["valid"] is False
    assert result["findings"] == ["verification receipt manifest validation failed"]


@pytest.mark.parametrize("finding", ["digest\ud800mismatch", "digest\udfffmismatch"])
def test_create_route_rejects_surrogate_post_build_finding(
    monkeypatch, finding: str
) -> None:
    receipt = {"schema": "receipt"}
    monkeypatch.setattr(
        routes,
        "build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda manifest: receipt,
    )
    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda candidate, manifest: [finding],
    )

    with pytest.raises(HTTPException) as exc_info:
        routes.create_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
            _create_payload(), current_user=object()  # type: ignore[arg-type]
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "invalid verification receipt manifest"


def test_validate_route_preserves_valid_supplementary_plane_finding(monkeypatch) -> None:
    expected = "digest mismatch 😀"
    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda receipt, manifest: [expected],
    )

    result = routes.validate_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
        _validation_payload(), current_user=object()  # type: ignore[arg-type]
    )

    assert result["findings"] == [expected]
