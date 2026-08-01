from pydantic import ValidationError

from app.api.routes import internal_alpha_comparison_archive_receipts as routes


def test_create_ledger_route_forwards_items(monkeypatch) -> None:
    items = [{"receipt": {"bundle_receipt_sha256": "a" * 64}, "bundle": {}}]
    expected = {"ledger_sha256": "b" * 64}
    seen: list[list[dict[str, object]]] = []

    def fake_build(payload: list[dict[str, object]]) -> dict[str, object]:
        seen.append(payload)
        return expected

    monkeypatch.setattr(
        routes,
        "build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger",
        fake_build,
    )
    payload = (
        routes.IntelligenceComparisonArchiveReceiptManifestBundleReceiptLedgerInput.model_validate(
            {"items": items}
        )
    )

    result = (
        routes.create_internal_alpha_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger(
            payload,
            current_user=object(),  # type: ignore[arg-type]
        )
    )

    assert result == expected
    assert seen == [items]


def test_validate_ledger_route_returns_bounded_findings(monkeypatch) -> None:
    ledger = {"ledger_sha256": "a" * 64}
    seen: list[dict[str, object]] = []

    def fake_validate(payload: dict[str, object]) -> list[str]:
        seen.append(payload)
        return ["bundle receipt ledger digest mismatch"]

    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger",
        fake_validate,
    )
    payload = routes.IntelligenceComparisonArchiveReceiptManifestBundleReceiptLedgerValidationInput.model_validate(
        {"ledger": ledger}
    )

    result = (
        routes.validate_internal_alpha_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger(
            payload,
            current_user=object(),  # type: ignore[arg-type]
        )
    )

    assert result["valid"] is False
    assert result["findings"] == ["bundle receipt ledger digest mismatch"]
    assert "does not infer causality" in result["interpretation_notice"]
    assert seen == [ledger]


def test_ledger_request_models_are_strict_and_bounded() -> None:
    try:
        routes.IntelligenceComparisonArchiveReceiptManifestBundleReceiptLedgerInput.model_validate(
            {"items": [{"receipt": {}, "bundle": {}}], "extra": True}
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("extra fields must be rejected")

    try:
        routes.IntelligenceComparisonArchiveReceiptManifestBundleReceiptLedgerInput.model_validate(
            {"items": []}
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("empty ledger input must be rejected")

    try:
        routes.IntelligenceComparisonArchiveReceiptManifestBundleReceiptLedgerValidationInput.model_validate(
            {"ledger": {}, "extra": True}
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("extra fields must be rejected")


def test_router_registers_ledger_paths() -> None:
    paths = {route.path for route in routes.router.routes}
    assert "/comparison/archive/receipt/manifest/bundle/receipt/ledger" in paths
    assert "/comparison/archive/receipt/manifest/bundle/receipt/ledger/validate" in paths
