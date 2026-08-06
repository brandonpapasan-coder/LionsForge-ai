import math

import pytest
from fastapi import HTTPException

from app.api.routes import (
    internal_alpha_comparison_archive_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipts as routes,
)


@pytest.mark.parametrize(
    "builder_output",
    [
        None,
        [],
        {1: "non-string key"},
        {"unsupported": object()},
        {"non_finite": math.nan},
    ],
)
def test_create_route_rejects_malformed_builder_outputs(
    monkeypatch, builder_output: object
) -> None:
    monkeypatch.setattr(
        routes,
        "build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda manifest: builder_output,
    )
    payload = routes.IntelligenceComparisonArchiveVerificationReceiptManifestVerificationReceiptInput.model_validate(
        {"manifest": {}}
    )

    with pytest.raises(HTTPException) as exc_info:
        routes.create_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
            payload,
            current_user=object(),  # type: ignore[arg-type]
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "invalid verification receipt manifest"


def test_create_route_accepts_exact_json_object(monkeypatch) -> None:
    expected = {
        "schema": "receipt",
        "schema_version": 1,
        "verified": True,
        "entry_count": 0,
        "optional": None,
        "nested": {"items": ["a", 2, False]},
    }
    monkeypatch.setattr(
        routes,
        "build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda manifest: expected,
    )
    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda receipt, manifest: [],
    )
    payload = routes.IntelligenceComparisonArchiveVerificationReceiptManifestVerificationReceiptInput.model_validate(
        {"manifest": {}}
    )

    result = routes.create_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
        payload,
        current_user=object(),  # type: ignore[arg-type]
    )

    assert result is expected


def test_create_route_bounds_expected_type_error(monkeypatch) -> None:
    def fake_build(manifest: dict[str, object]) -> dict[str, object]:
        raise TypeError("internal builder detail must not leak")

    monkeypatch.setattr(
        routes,
        "build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        fake_build,
    )
    payload = routes.IntelligenceComparisonArchiveVerificationReceiptManifestVerificationReceiptInput.model_validate(
        {"manifest": {}}
    )

    with pytest.raises(HTTPException) as exc_info:
        routes.create_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
            payload,
            current_user=object(),  # type: ignore[arg-type]
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "invalid verification receipt manifest"


def test_create_route_does_not_mask_unexpected_builder_error(monkeypatch) -> None:
    def fake_build(manifest: dict[str, object]) -> dict[str, object]:
        raise RuntimeError("unexpected defect")

    monkeypatch.setattr(
        routes,
        "build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        fake_build,
    )
    payload = routes.IntelligenceComparisonArchiveVerificationReceiptManifestVerificationReceiptInput.model_validate(
        {"manifest": {}}
    )

    with pytest.raises(RuntimeError, match="unexpected defect"):
        routes.create_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
            payload,
            current_user=object(),  # type: ignore[arg-type]
        )
