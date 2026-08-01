from typing import Any

from pydantic import ValidationError

from app.api.routes import (
    internal_alpha_comparison_archive_receipt_ledger_receipt_manifest_verification_receipt_manifests as routes,
)
from app.main import app


def test_create_route_forwards_entries(monkeypatch) -> None:
    entries = [{"receipt": {"digest": "a"}, "manifest": {"digest": "b"}}]
    expected = {"manifest_sha256": "c" * 64}
    captured: dict[str, Any] = {}

    def fake_build(value: list[dict[str, Any]]) -> dict[str, Any]:
        captured["entries"] = value
        return expected

    monkeypatch.setattr(
        routes,
        "build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest",
        fake_build,
    )
    payload = routes.IntelligenceComparisonArchiveReceiptLedgerReceiptManifestVerificationReceiptManifestInput(
        entries=entries
    )

    result = routes.create_internal_alpha_intelligence_comparison_archive_receipt_ledger_receipt_manifest_verification_receipt_manifest(
        payload,
        current_user=object(),
    )

    assert result == expected
    assert captured == {"entries": entries}


def test_validate_route_forwards_manifest_and_returns_findings(monkeypatch) -> None:
    manifest = {"manifest_sha256": "d" * 64}
    expected_findings = ["verification receipt manifest digest mismatch"]
    captured: dict[str, Any] = {}

    def fake_validate(value: dict[str, Any]) -> list[str]:
        captured["manifest"] = value
        return expected_findings

    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest",
        fake_validate,
    )
    payload = routes.IntelligenceComparisonArchiveReceiptLedgerReceiptManifestVerificationReceiptManifestValidationInput(
        manifest=manifest
    )

    result = routes.validate_internal_alpha_intelligence_comparison_archive_receipt_ledger_receipt_manifest_verification_receipt_manifest(
        payload,
        current_user=object(),
    )

    assert captured == {"manifest": manifest}
    assert result["valid"] is False
    assert result["findings"] == expected_findings
    assert "does not infer causality" in result["interpretation_notice"]
    assert "authorize any release transition" in result["interpretation_notice"]


def test_request_models_reject_unknown_fields() -> None:
    try:
        routes.IntelligenceComparisonArchiveReceiptLedgerReceiptManifestVerificationReceiptManifestInput(
            entries=[{}],
            unexpected=True,
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("creation input accepted an unknown field")

    try:
        routes.IntelligenceComparisonArchiveReceiptLedgerReceiptManifestVerificationReceiptManifestValidationInput(
            manifest={},
            unexpected=True,
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("validation input accepted an unknown field")


def test_creation_input_enforces_bounded_entries() -> None:
    for entries in ([], [{}] * 101):
        try:
            routes.IntelligenceComparisonArchiveReceiptLedgerReceiptManifestVerificationReceiptManifestInput(
                entries=entries
            )
        except ValidationError:
            continue
        raise AssertionError("creation input accepted an out-of-bounds entry list")


def test_exact_routes_are_registered_and_authenticated() -> None:
    base = (
        "/api/v1/internal-alpha/intelligence/comparison/archive/receipt/manifest/"
        "bundle/receipt/ledger/receipt/manifest/verification-receipt/manifest"
    )
    schema = app.openapi()

    assert base in schema["paths"]
    assert f"{base}/validate" in schema["paths"]
    assert "post" in schema["paths"][base]
    assert "post" in schema["paths"][f"{base}/validate"]
    assert schema["paths"][base]["post"]["security"]
    assert schema["paths"][f"{base}/validate"]["post"]["security"]
