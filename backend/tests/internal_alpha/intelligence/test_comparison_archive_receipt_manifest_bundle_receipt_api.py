from pydantic import ValidationError

from app.api.routes import internal_alpha_comparison_archive_receipts as routes


def test_create_bundle_receipt_route_forwards_bundle(monkeypatch) -> None:
    bundle = {"bundle_sha256": "a" * 64, "entry_count": 1}
    expected = {"bundle_receipt_sha256": "b" * 64}
    seen: list[dict[str, object]] = []

    def fake_build(payload: dict[str, object]) -> dict[str, object]:
        seen.append(payload)
        return expected

    monkeypatch.setattr(
        routes,
        "build_intelligence_comparison_archive_receipt_manifest_bundle_receipt",
        fake_build,
    )
    payload = (
        routes.IntelligenceComparisonArchiveReceiptManifestBundleReceiptInput.model_validate(
            {"bundle": bundle}
        )
    )

    result = (
        routes.create_internal_alpha_intelligence_comparison_archive_receipt_manifest_bundle_receipt(
            payload,
            current_user=object(),  # type: ignore[arg-type]
        )
    )

    assert result == expected
    assert seen == [bundle]


def test_validate_bundle_receipt_route_returns_bounded_findings(monkeypatch) -> None:
    bundle = {"bundle_sha256": "a" * 64, "entry_count": 1}
    receipt = {"bundle_receipt_sha256": "b" * 64}
    seen: list[tuple[dict[str, object], dict[str, object]]] = []

    def fake_validate(
        supplied_receipt: dict[str, object],
        supplied_bundle: dict[str, object],
    ) -> list[str]:
        seen.append((supplied_receipt, supplied_bundle))
        return ["comparison archive receipt manifest bundle receipt digest mismatch"]

    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt",
        fake_validate,
    )
    payload = (
        routes.IntelligenceComparisonArchiveReceiptManifestBundleReceiptValidationInput.model_validate(
            {"receipt": receipt, "bundle": bundle}
        )
    )

    result = (
        routes.validate_internal_alpha_intelligence_comparison_archive_receipt_manifest_bundle_receipt(
            payload,
            current_user=object(),  # type: ignore[arg-type]
        )
    )

    assert result["valid"] is False
    assert result["findings"] == [
        "comparison archive receipt manifest bundle receipt digest mismatch"
    ]
    assert "does not infer causality" in result["interpretation_notice"]
    assert seen == [(receipt, bundle)]


def test_bundle_receipt_request_models_forbid_extra_fields() -> None:
    try:
        routes.IntelligenceComparisonArchiveReceiptManifestBundleReceiptInput.model_validate(
            {"bundle": {}, "extra": True}
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("extra fields must be rejected")

    try:
        routes.IntelligenceComparisonArchiveReceiptManifestBundleReceiptValidationInput.model_validate(
            {"receipt": {}, "bundle": {}, "extra": True}
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("extra fields must be rejected")


def test_router_registers_bundle_receipt_paths() -> None:
    paths = {route.path for route in routes.router.routes}
    assert "/comparison/archive/receipt/manifest/bundle/receipt" in paths
    assert "/comparison/archive/receipt/manifest/bundle/receipt/validate" in paths
