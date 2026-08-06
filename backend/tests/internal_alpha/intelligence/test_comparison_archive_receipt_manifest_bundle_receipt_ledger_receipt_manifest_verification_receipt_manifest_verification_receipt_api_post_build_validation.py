import pytest
from fastapi import HTTPException

from app.api.routes import (
    internal_alpha_comparison_archive_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipts as routes,
)


def _payload() -> routes.IntelligenceComparisonArchiveVerificationReceiptManifestVerificationReceiptInput:
    return routes.IntelligenceComparisonArchiveVerificationReceiptManifestVerificationReceiptInput.model_validate(
        {"manifest": {"verification_receipt_manifest_sha256": "a" * 64, "entry_count": 2}}
    )


def test_create_route_returns_builder_receipt_only_after_empty_validation(monkeypatch) -> None:
    receipt = {"schema": "receipt", "schema_version": 1}
    seen: list[tuple[dict[str, object], dict[str, object]]] = []
    monkeypatch.setattr(
        routes,
        "build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda manifest: receipt,
    )

    def fake_validate(
        candidate_receipt: dict[str, object],
        candidate_manifest: dict[str, object],
    ) -> list[str]:
        seen.append((candidate_receipt, candidate_manifest))
        return []

    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        fake_validate,
    )

    result = routes.create_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
        _payload(),
        current_user=object(),  # type: ignore[arg-type]
    )

    assert result is receipt
    assert seen == [(receipt, _payload().manifest)]


@pytest.mark.parametrize(
    "findings",
    [
        ["schema mismatch"],
        None,
        ("schema mismatch",),
        "schema mismatch",
        [1],
    ],
)
def test_create_route_returns_bounded_422_for_nonempty_or_malformed_validation_result(
    monkeypatch,
    findings: object,
) -> None:
    monkeypatch.setattr(
        routes,
        "build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda manifest: {"schema": "receipt"},
    )
    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda receipt, manifest: findings,
    )

    with pytest.raises(HTTPException) as exc_info:
        routes.create_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
            _payload(),
            current_user=object(),  # type: ignore[arg-type]
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "invalid verification receipt manifest"


@pytest.mark.parametrize("error_type", [TypeError, ValueError])
def test_create_route_returns_bounded_422_for_expected_post_build_validation_errors(
    monkeypatch,
    error_type: type[Exception],
) -> None:
    monkeypatch.setattr(
        routes,
        "build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda manifest: {"schema": "receipt"},
    )

    def fake_validate(receipt: dict[str, object], manifest: dict[str, object]) -> list[str]:
        raise error_type("internal validation details must not leak")

    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        fake_validate,
    )

    with pytest.raises(HTTPException) as exc_info:
        routes.create_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
            _payload(),
            current_user=object(),  # type: ignore[arg-type]
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "invalid verification receipt manifest"


def test_create_route_does_not_mask_unexpected_post_build_validation_error(monkeypatch) -> None:
    monkeypatch.setattr(
        routes,
        "build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda manifest: {"schema": "receipt"},
    )

    def fake_validate(receipt: dict[str, object], manifest: dict[str, object]) -> list[str]:
        raise RuntimeError("programming defect")

    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        fake_validate,
    )

    with pytest.raises(RuntimeError, match="programming defect"):
        routes.create_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
            _payload(),
            current_user=object(),  # type: ignore[arg-type]
        )
