from pydantic import ValidationError

from app.api.routes import internal_alpha_comparison_archive_receipts as routes


def test_create_manifest_receipt_route_forwards_manifest(monkeypatch) -> None:
    manifest = {"manifest_sha256": "a" * 64, "entry_count": 1}
    expected = {"receipt_sha256": "b" * 64}
    seen: list[dict[str, object]] = []

    def fake_build(payload: dict[str, object]) -> dict[str, object]:
        seen.append(payload)
        return expected

    monkeypatch.setattr(
        routes,
        "build_intelligence_comparison_archive_receipt_manifest_receipt",
        fake_build,
    )
    payload = (
        routes.IntelligenceComparisonArchiveReceiptManifestReceiptInput.model_validate(
            {"manifest": manifest}
        )
    )

    result = (
        routes.create_internal_alpha_intelligence_comparison_archive_receipt_manifest_receipt(
            payload,
            current_user=object(),  # type: ignore[arg-type]
        )
    )

    assert result == expected
    assert seen == [manifest]


def test_validate_manifest_receipt_route_returns_bounded_findings(monkeypatch) -> None:
    manifest = {"manifest_sha256": "a" * 64, "entry_count": 1}
    receipt = {"receipt_sha256": "b" * 64}
    seen: list[tuple[dict[str, object], dict[str, object]]] = []

    def fake_validate(
        supplied_receipt: dict[str, object],
        supplied_manifest: dict[str, object],
    ) -> list[str]:
        seen.append((supplied_receipt, supplied_manifest))
        return ["comparison archive receipt manifest receipt digest mismatch"]

    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest_receipt",
        fake_validate,
    )
    payload = routes.IntelligenceComparisonArchiveReceiptManifestReceiptValidationInput.model_validate(
        {"receipt": receipt, "manifest": manifest}
    )

    result = (
        routes.validate_internal_alpha_intelligence_comparison_archive_receipt_manifest_receipt(
            payload,
            current_user=object(),  # type: ignore[arg-type]
        )
    )

    assert result["valid"] is False
    assert result["findings"] == [
        "comparison archive receipt manifest receipt digest mismatch"
    ]
    assert "does not infer causality" in result["interpretation_notice"]
    assert seen == [(receipt, manifest)]


def test_manifest_receipt_request_models_forbid_extra_fields() -> None:
    try:
        routes.IntelligenceComparisonArchiveReceiptManifestReceiptInput.model_validate(
            {"manifest": {}, "extra": True}
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("extra fields must be rejected")

    try:
        routes.IntelligenceComparisonArchiveReceiptManifestReceiptValidationInput.model_validate(
            {"receipt": {}, "manifest": {}, "extra": True}
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("extra fields must be rejected")


def test_router_registers_manifest_receipt_paths() -> None:
    paths = {route.path for route in routes.router.routes}
    assert "/comparison/archive/receipt/manifest/receipt" in paths
    assert "/comparison/archive/receipt/manifest/receipt/validate" in paths
