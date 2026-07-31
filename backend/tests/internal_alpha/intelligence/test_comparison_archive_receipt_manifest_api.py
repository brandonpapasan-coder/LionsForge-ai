from pydantic import ValidationError

from app.api.routes import internal_alpha_comparison_archive_receipts as routes


def test_create_manifest_route_forwards_entries(monkeypatch) -> None:
    entries = [{"archive": {}, "receipt": {}}]
    expected = {"manifest_sha256": "a" * 64}
    seen: list[list[dict[str, object]]] = []

    def fake_build(payload: list[dict[str, object]]) -> dict[str, object]:
        seen.append(payload)
        return expected

    monkeypatch.setattr(
        routes,
        "build_intelligence_comparison_archive_receipt_manifest",
        fake_build,
    )
    payload = routes.IntelligenceComparisonArchiveReceiptManifestInput.model_validate(
        {"entries": entries}
    )

    result = routes.create_internal_alpha_intelligence_comparison_archive_receipt_manifest(
        payload,
        current_user=object(),  # type: ignore[arg-type]
    )

    assert result == expected
    assert seen == [entries]


def test_validate_manifest_route_returns_bounded_findings(monkeypatch) -> None:
    manifest = {"manifest_sha256": "a" * 64}
    seen: list[dict[str, object]] = []

    def fake_validate(payload: dict[str, object]) -> list[str]:
        seen.append(payload)
        return ["comparison archive receipt manifest digest mismatch"]

    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest",
        fake_validate,
    )
    payload = routes.IntelligenceComparisonArchiveReceiptManifestValidationInput.model_validate(
        {"manifest": manifest}
    )

    result = routes.validate_internal_alpha_intelligence_comparison_archive_receipt_manifest(
        payload,
        current_user=object(),  # type: ignore[arg-type]
    )

    assert result["valid"] is False
    assert result["findings"] == [
        "comparison archive receipt manifest digest mismatch"
    ]
    assert "does not infer causality" in result["interpretation_notice"]
    assert seen == [manifest]


def test_manifest_request_models_are_strict_and_bounded() -> None:
    for value in ([], [{}] * 101):
        try:
            routes.IntelligenceComparisonArchiveReceiptManifestInput.model_validate(
                {"entries": value}
            )
        except ValidationError:
            pass
        else:
            raise AssertionError("manifest entries must contain 1 to 100 items")

    try:
        routes.IntelligenceComparisonArchiveReceiptManifestInput.model_validate(
            {"entries": [{}], "extra": True}
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("extra fields must be rejected")

    try:
        routes.IntelligenceComparisonArchiveReceiptManifestValidationInput.model_validate(
            {"manifest": {}, "extra": True}
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("extra fields must be rejected")


def test_router_registers_manifest_paths() -> None:
    paths = {route.path for route in routes.router.routes}
    assert "/comparison/archive/receipt/manifest" in paths
    assert "/comparison/archive/receipt/manifest/validate" in paths
