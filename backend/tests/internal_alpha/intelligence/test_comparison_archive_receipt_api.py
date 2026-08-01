from pydantic import ValidationError

from app.api.routes import internal_alpha_comparison_archive_receipts as routes


def test_create_route_forwards_archive(monkeypatch) -> None:
    archive = {"archive_sha256": "a" * 64}
    expected = {"receipt_sha256": "b" * 64}
    seen: list[dict[str, object]] = []

    def fake_build(payload: dict[str, object]) -> dict[str, object]:
        seen.append(payload)
        return expected

    monkeypatch.setattr(routes, "build_intelligence_comparison_archive_receipt", fake_build)
    payload = routes.IntelligenceComparisonArchiveReceiptInput.model_validate(
        {"archive": archive}
    )

    result = routes.create_internal_alpha_intelligence_comparison_archive_receipt(
        payload,
        current_user=object(),  # type: ignore[arg-type]
    )

    assert result == expected
    assert seen == [archive]


def test_validate_route_returns_bounded_findings(monkeypatch) -> None:
    archive = {"archive_sha256": "a" * 64}
    receipt = {"receipt_sha256": "b" * 64}
    seen: list[tuple[dict[str, object], dict[str, object]]] = []

    def fake_validate(
        supplied_receipt: dict[str, object],
        supplied_archive: dict[str, object],
    ) -> list[str]:
        seen.append((supplied_receipt, supplied_archive))
        return ["comparison archive receipt digest mismatch"]

    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt",
        fake_validate,
    )
    payload = routes.IntelligenceComparisonArchiveReceiptValidationInput.model_validate(
        {"receipt": receipt, "archive": archive}
    )

    result = routes.validate_internal_alpha_intelligence_comparison_archive_receipt(
        payload,
        current_user=object(),  # type: ignore[arg-type]
    )

    assert result["valid"] is False
    assert result["findings"] == ["comparison archive receipt digest mismatch"]
    assert "does not infer causality" in result["interpretation_notice"]
    assert seen == [(receipt, archive)]


def test_request_models_forbid_extra_fields() -> None:
    try:
        routes.IntelligenceComparisonArchiveReceiptInput.model_validate(
            {"archive": {}, "extra": True}
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("extra fields must be rejected")

    try:
        routes.IntelligenceComparisonArchiveReceiptValidationInput.model_validate(
            {"receipt": {}, "archive": {}, "extra": True}
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("extra fields must be rejected")


def test_router_registers_expected_paths() -> None:
    paths = {route.path for route in routes.router.routes}
    assert paths == {
        "/comparison/archive/receipt",
        "/comparison/archive/receipt/validate",
        "/comparison/archive/receipt/manifest",
        "/comparison/archive/receipt/manifest/validate",
        "/comparison/archive/receipt/manifest/receipt",
        "/comparison/archive/receipt/manifest/receipt/validate",
    }
