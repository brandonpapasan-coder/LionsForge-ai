from pydantic import ValidationError

from app.api.routes import internal_alpha_comparison_archive_receipt_ledger_receipts as routes


def test_create_route_forwards_ledger(monkeypatch) -> None:
    ledger = {"ledger_sha256": "a" * 64}
    expected = {"ledger_receipt_sha256": "b" * 64}
    seen: list[dict[str, object]] = []

    def fake_build(payload: dict[str, object]) -> dict[str, object]:
        seen.append(payload)
        return expected

    monkeypatch.setattr(
        routes,
        "build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt",
        fake_build,
    )
    payload = (
        routes.IntelligenceComparisonArchiveReceiptManifestBundleReceiptLedgerReceiptInput.model_validate(
            {"ledger": ledger}
        )
    )

    result = routes.create_internal_alpha_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt(
        payload,
        current_user=object(),  # type: ignore[arg-type]
    )

    assert result == expected
    assert seen == [ledger]


def test_validate_route_returns_fail_closed_findings(monkeypatch) -> None:
    ledger = {"ledger_sha256": "a" * 64}
    receipt = {"ledger_receipt_sha256": "b" * 64}
    seen: list[tuple[dict[str, object], dict[str, object]]] = []

    def fake_validate(
        supplied_receipt: dict[str, object],
        supplied_ledger: dict[str, object],
    ) -> list[str]:
        seen.append((supplied_receipt, supplied_ledger))
        return ["comparison archive bundle receipt ledger receipt digest mismatch"]

    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt",
        fake_validate,
    )
    payload = routes.IntelligenceComparisonArchiveReceiptManifestBundleReceiptLedgerReceiptValidationInput.model_validate(
        {"receipt": receipt, "ledger": ledger}
    )

    result = routes.validate_internal_alpha_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt(
        payload,
        current_user=object(),  # type: ignore[arg-type]
    )

    assert result["valid"] is False
    assert result["findings"] == [
        "comparison archive bundle receipt ledger receipt digest mismatch"
    ]
    assert "does not infer causality" in result["interpretation_notice"]
    assert seen == [(receipt, ledger)]


def test_request_models_forbid_extra_fields() -> None:
    for model, payload in (
        (
            routes.IntelligenceComparisonArchiveReceiptManifestBundleReceiptLedgerReceiptInput,
            {"ledger": {}, "extra": True},
        ),
        (
            routes.IntelligenceComparisonArchiveReceiptManifestBundleReceiptLedgerReceiptValidationInput,
            {"receipt": {}, "ledger": {}, "extra": True},
        ),
    ):
        try:
            model.model_validate(payload)
        except ValidationError:
            pass
        else:
            raise AssertionError("extra fields must be rejected")


def test_router_registers_exact_paths() -> None:
    paths = {route.path for route in routes.router.routes}
    assert paths == {
        "/comparison/archive/receipt/manifest/bundle/receipt/ledger/receipt",
        "/comparison/archive/receipt/manifest/bundle/receipt/ledger/receipt/validate",
    }
