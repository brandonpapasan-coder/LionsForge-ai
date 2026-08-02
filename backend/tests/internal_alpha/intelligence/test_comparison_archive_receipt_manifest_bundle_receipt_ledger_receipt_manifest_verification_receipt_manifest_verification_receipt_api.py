from pydantic import ValidationError

from app.api.routes import (
    internal_alpha_comparison_archive_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipts as routes,
)


def test_create_route_forwards_manifest(monkeypatch) -> None:
    manifest = {"verification_receipt_manifest_sha256": "a" * 64, "entry_count": 2}
    expected = {
        "verification_receipt_manifest_verification_receipt_sha256": "b" * 64
    }
    seen: list[dict[str, object]] = []

    def fake_build(payload: dict[str, object]) -> dict[str, object]:
        seen.append(payload)
        return expected

    monkeypatch.setattr(
        routes,
        "build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        fake_build,
    )
    payload = routes.IntelligenceComparisonArchiveVerificationReceiptManifestVerificationReceiptInput.model_validate(
        {"manifest": manifest}
    )

    result = routes.create_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
        payload,
        current_user=object(),  # type: ignore[arg-type]
    )

    assert result == expected
    assert seen == [manifest]


def test_validate_route_forwards_receipt_and_manifest(monkeypatch) -> None:
    receipt = {
        "verification_receipt_manifest_verification_receipt_sha256": "b" * 64
    }
    manifest = {"verification_receipt_manifest_sha256": "a" * 64, "entry_count": 2}
    seen: list[tuple[dict[str, object], dict[str, object]]] = []

    def fake_validate(
        candidate_receipt: dict[str, object],
        candidate_manifest: dict[str, object],
    ) -> list[str]:
        seen.append((candidate_receipt, candidate_manifest))
        return ["verification receipt manifest verification receipt digest mismatch"]

    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        fake_validate,
    )
    payload = routes.IntelligenceComparisonArchiveVerificationReceiptManifestVerificationReceiptValidationInput.model_validate(
        {"receipt": receipt, "manifest": manifest}
    )

    result = routes.validate_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
        payload,
        current_user=object(),  # type: ignore[arg-type]
    )

    assert result["valid"] is False
    assert result["findings"] == [
        "verification receipt manifest verification receipt digest mismatch"
    ]
    assert "does not infer causality" in result["interpretation_notice"]
    assert seen == [(receipt, manifest)]


def test_request_models_reject_extra_fields() -> None:
    try:
        routes.IntelligenceComparisonArchiveVerificationReceiptManifestVerificationReceiptInput.model_validate(
            {"manifest": {}, "extra": True}
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("extra receipt creation fields must be rejected")

    try:
        routes.IntelligenceComparisonArchiveVerificationReceiptManifestVerificationReceiptValidationInput.model_validate(
            {"receipt": {}, "manifest": {}, "extra": True}
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("extra receipt validation fields must be rejected")


def test_router_registers_exact_paths() -> None:
    paths = {route.path for route in routes.router.routes}
    assert paths == {
        "/comparison/archive/receipt/manifest/bundle/receipt/ledger/receipt/manifest/verification-receipt/manifest/verification-receipt",
        "/comparison/archive/receipt/manifest/bundle/receipt/ledger/receipt/manifest/verification-receipt/manifest/verification-receipt/validate",
    }
