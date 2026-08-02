from pydantic import ValidationError

from app.api.routes import internal_alpha_comparison_archive_integrity_reports as routes


def test_create_route_forwards_receipt_and_manifest(monkeypatch) -> None:
    receipt = {"verification_receipt_manifest_verification_receipt_sha256": "b" * 64}
    manifest = {"verification_receipt_manifest_sha256": "a" * 64, "entry_count": 2}
    expected = {"integrity_report_sha256": "c" * 64}
    seen: list[tuple[dict[str, object], dict[str, object]]] = []

    def fake_build(
        candidate_receipt: dict[str, object],
        candidate_manifest: dict[str, object],
    ) -> dict[str, object]:
        seen.append((candidate_receipt, candidate_manifest))
        return expected

    monkeypatch.setattr(routes, "build_intelligence_comparison_archive_integrity_report", fake_build)
    payload = routes.IntelligenceComparisonArchiveIntegrityReportInput.model_validate(
        {"receipt": receipt, "manifest": manifest}
    )

    result = routes.create_internal_alpha_intelligence_comparison_archive_integrity_report(
        payload,
        current_user=object(),  # type: ignore[arg-type]
    )

    assert result == expected
    assert seen == [(receipt, manifest)]


def test_validate_route_forwards_exact_sources_and_findings(monkeypatch) -> None:
    report = {"integrity_report_sha256": "c" * 64}
    receipt = {"verification_receipt_manifest_verification_receipt_sha256": "b" * 64}
    manifest = {"verification_receipt_manifest_sha256": "a" * 64, "entry_count": 2}
    seen: list[tuple[dict[str, object], dict[str, object], dict[str, object]]] = []

    def fake_validate(
        candidate_report: dict[str, object],
        candidate_receipt: dict[str, object],
        candidate_manifest: dict[str, object],
    ) -> list[str]:
        seen.append((candidate_report, candidate_receipt, candidate_manifest))
        return ["integrity report digest mismatch"]

    monkeypatch.setattr(routes, "validate_intelligence_comparison_archive_integrity_report", fake_validate)
    payload = routes.IntelligenceComparisonArchiveIntegrityReportValidationInput.model_validate(
        {"report": report, "receipt": receipt, "manifest": manifest}
    )

    result = routes.validate_internal_alpha_intelligence_comparison_archive_integrity_report(
        payload,
        current_user=object(),  # type: ignore[arg-type]
    )

    assert result["valid"] is False
    assert result["findings"] == ["integrity report digest mismatch"]
    assert "does not infer causality" in result["interpretation_notice"]
    assert seen == [(report, receipt, manifest)]


def test_request_models_reject_extra_fields() -> None:
    try:
        routes.IntelligenceComparisonArchiveIntegrityReportInput.model_validate(
            {"receipt": {}, "manifest": {}, "extra": True}
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("extra integrity report creation fields must be rejected")

    try:
        routes.IntelligenceComparisonArchiveIntegrityReportValidationInput.model_validate(
            {"report": {}, "receipt": {}, "manifest": {}, "extra": True}
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("extra integrity report validation fields must be rejected")


def test_routes_require_authentication_dependency() -> None:
    for route in routes.router.routes:
        assert route.dependant.dependencies


def test_router_registers_exact_paths() -> None:
    paths = {route.path for route in routes.router.routes}
    assert paths == {
        "/comparison/archive/integrity-report",
        "/comparison/archive/integrity-report/validate",
    }
