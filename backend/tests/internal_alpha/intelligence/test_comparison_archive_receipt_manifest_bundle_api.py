from pydantic import ValidationError

from app.api.routes import internal_alpha_comparison_archive_receipts as routes


def test_create_manifest_bundle_route_forwards_chain(monkeypatch) -> None:
    manifest = {"manifest_sha256": "a" * 64, "entry_count": 1}
    receipt = {"receipt_sha256": "b" * 64}
    expected = {"bundle_sha256": "c" * 64}
    seen: list[tuple[dict[str, object], dict[str, object]]] = []

    def fake_build(
        supplied_manifest: dict[str, object],
        supplied_receipt: dict[str, object],
    ) -> dict[str, object]:
        seen.append((supplied_manifest, supplied_receipt))
        return expected

    monkeypatch.setattr(
        routes,
        "build_intelligence_comparison_archive_receipt_manifest_bundle",
        fake_build,
    )
    payload = routes.IntelligenceComparisonArchiveReceiptManifestBundleInput.model_validate(
        {"manifest": manifest, "receipt": receipt}
    )

    result = routes.create_internal_alpha_intelligence_comparison_archive_receipt_manifest_bundle(
        payload,
        current_user=object(),  # type: ignore[arg-type]
    )

    assert result == expected
    assert seen == [(manifest, receipt)]


def test_validate_manifest_bundle_route_returns_bounded_findings(monkeypatch) -> None:
    bundle = {"bundle_sha256": "c" * 64}
    seen: list[dict[str, object]] = []

    def fake_validate(supplied_bundle: dict[str, object]) -> list[str]:
        seen.append(supplied_bundle)
        return ["comparison archive receipt manifest bundle digest mismatch"]

    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle",
        fake_validate,
    )
    payload = (
        routes.IntelligenceComparisonArchiveReceiptManifestBundleValidationInput.model_validate(
            {"bundle": bundle}
        )
    )

    result = routes.validate_internal_alpha_intelligence_comparison_archive_receipt_manifest_bundle(
        payload,
        current_user=object(),  # type: ignore[arg-type]
    )

    assert result["valid"] is False
    assert result["findings"] == [
        "comparison archive receipt manifest bundle digest mismatch"
    ]
    assert "does not infer causality" in result["interpretation_notice"]
    assert seen == [bundle]


def test_manifest_bundle_request_models_forbid_extra_fields() -> None:
    try:
        routes.IntelligenceComparisonArchiveReceiptManifestBundleInput.model_validate(
            {"manifest": {}, "receipt": {}, "extra": True}
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("extra fields must be rejected")

    try:
        routes.IntelligenceComparisonArchiveReceiptManifestBundleValidationInput.model_validate(
            {"bundle": {}, "extra": True}
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("extra fields must be rejected")


def test_router_registers_manifest_bundle_paths() -> None:
    paths = {route.path for route in routes.router.routes}
    assert "/comparison/archive/receipt/manifest/bundle" in paths
    assert "/comparison/archive/receipt/manifest/bundle/validate" in paths
