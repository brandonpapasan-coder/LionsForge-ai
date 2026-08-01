from pydantic import ValidationError

from app.api.routes import (
    internal_alpha_comparison_archive_receipt_ledger_receipt_manifests as routes,
)


def test_create_route_forwards_entries(monkeypatch) -> None:
    entries = [{"receipt": {"ledger_receipt_sha256": "a" * 64}, "ledger": {}}]
    expected = {"manifest_sha256": "b" * 64}
    seen: list[list[dict[str, object]]] = []

    def fake_build(payload: list[dict[str, object]]) -> dict[str, object]:
        seen.append(payload)
        return expected

    monkeypatch.setattr(
        routes,
        "build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest",
        fake_build,
    )
    payload = routes.IntelligenceComparisonArchiveReceiptLedgerReceiptManifestInput.model_validate(
        {"entries": entries}
    )

    result = routes.create_internal_alpha_intelligence_comparison_archive_receipt_ledger_receipt_manifest(
        payload,
        current_user=object(),  # type: ignore[arg-type]
    )

    assert result == expected
    assert seen == [entries]


def test_validate_route_returns_fail_closed_findings(monkeypatch) -> None:
    manifest = {"manifest_sha256": "a" * 64}
    seen: list[dict[str, object]] = []

    def fake_validate(payload: dict[str, object]) -> list[str]:
        seen.append(payload)
        return ["ledger receipt manifest digest mismatch"]

    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest",
        fake_validate,
    )
    payload = (
        routes.IntelligenceComparisonArchiveReceiptLedgerReceiptManifestValidationInput.model_validate(
            {"manifest": manifest}
        )
    )

    result = routes.validate_internal_alpha_intelligence_comparison_archive_receipt_ledger_receipt_manifest(
        payload,
        current_user=object(),  # type: ignore[arg-type]
    )

    assert result["valid"] is False
    assert result["findings"] == ["ledger receipt manifest digest mismatch"]
    assert "does not infer causality" in result["interpretation_notice"]
    assert seen == [manifest]


def test_request_models_are_strict_and_bounded() -> None:
    for payload in ({"entries": []}, {"entries": [{}] * 101}, {"entries": [{}], "extra": True}):
        try:
            routes.IntelligenceComparisonArchiveReceiptLedgerReceiptManifestInput.model_validate(
                payload
            )
        except ValidationError:
            pass
        else:
            raise AssertionError("invalid manifest creation payload must be rejected")

    try:
        routes.IntelligenceComparisonArchiveReceiptLedgerReceiptManifestValidationInput.model_validate(
            {"manifest": {}, "extra": True}
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("extra validation fields must be rejected")


def test_router_registers_exact_paths() -> None:
    paths = {route.path for route in routes.router.routes}
    assert paths == {
        "/comparison/archive/receipt/manifest/bundle/receipt/ledger/receipt/manifest",
        "/comparison/archive/receipt/manifest/bundle/receipt/ledger/receipt/manifest/validate",
    }
