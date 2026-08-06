import pytest
from fastapi import HTTPException

from app.api.routes import (
    internal_alpha_comparison_archive_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipts as routes,
)


def _validation_payload():
    return routes.IntelligenceComparisonArchiveVerificationReceiptManifestVerificationReceiptValidationInput.model_validate(
        {"receipt": {}, "manifest": {}}
    )


def _create_payload():
    return routes.IntelligenceComparisonArchiveVerificationReceiptManifestVerificationReceiptInput.model_validate(
        {"manifest": {}}
    )


def test_validate_route_replaces_empty_finding_with_generic_failure(monkeypatch) -> None:
    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda receipt, manifest: [""],
    )

    result = routes.validate_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
        _validation_payload(), current_user=object()  # type: ignore[arg-type]
    )

    assert result["valid"] is False
    assert result["findings"] == ["verification receipt manifest validation failed"]


@pytest.mark.parametrize("blank_finding", [" ", "\t", "\n", " \t\n "])
def test_validate_route_replaces_whitespace_only_finding_with_generic_failure(
    monkeypatch, blank_finding: str
) -> None:
    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda receipt, manifest: [blank_finding],
    )

    result = routes.validate_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
        _validation_payload(), current_user=object()  # type: ignore[arg-type]
    )

    assert result["valid"] is False
    assert result["findings"] == ["verification receipt manifest validation failed"]


@pytest.mark.parametrize(
    "finding",
    [
        "digest mismatch\nforged line",
        "digest\tmismatch",
        "digest\rmismatch",
        "digest\x00mismatch",
        "digest\x1fmismatch",
        "digest\x7fmismatch",
        "digest\x80mismatch",
        "digest\x85mismatch",
        "digest\x9bmismatch",
        "digest\x9fmismatch",
    ],
)
def test_validate_route_replaces_control_character_finding_with_generic_failure(
    monkeypatch, finding: str
) -> None:
    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda receipt, manifest: [finding],
    )

    result = routes.validate_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
        _validation_payload(), current_user=object()  # type: ignore[arg-type]
    )

    assert result["valid"] is False
    assert result["findings"] == ["verification receipt manifest validation failed"]


@pytest.mark.parametrize(
    "finding",
    [
        "digest\u200bmismatch",
        "digest\u2060mismatch",
        "digest\u202emismatch",
        "digest\u2066mismatch",
        "digest\ufeffmismatch",
    ],
)
def test_validate_route_replaces_unicode_format_finding_with_generic_failure(
    monkeypatch, finding: str
) -> None:
    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda receipt, manifest: [finding],
    )

    result = routes.validate_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
        _validation_payload(), current_user=object()  # type: ignore[arg-type]
    )

    assert result["valid"] is False
    assert result["findings"] == ["verification receipt manifest validation failed"]


def test_validate_route_preserves_nonempty_finding(monkeypatch) -> None:
    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda receipt, manifest: ["digest mismatch"],
    )

    result = routes.validate_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
        _validation_payload(), current_user=object()  # type: ignore[arg-type]
    )

    assert result["findings"] == ["digest mismatch"]


def test_validate_route_preserves_meaningful_finding_whitespace(monkeypatch) -> None:
    expected = "  digest mismatch  "
    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda receipt, manifest: [expected],
    )

    result = routes.validate_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
        _validation_payload(), current_user=object()  # type: ignore[arg-type]
    )

    assert result["findings"] == [expected]


def test_validate_route_preserves_visible_unicode_finding(monkeypatch) -> None:
    expected = "résumé digest mismatch — section §2"
    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda receipt, manifest: [expected],
    )

    result = routes.validate_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
        _validation_payload(), current_user=object()  # type: ignore[arg-type]
    )

    assert result["findings"] == [expected]


def test_validate_route_preserves_combining_mark_finding(monkeypatch) -> None:
    expected = "re\u0301sume\u0301 digest mismatch"
    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda receipt, manifest: [expected],
    )

    result = routes.validate_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
        _validation_payload(), current_user=object()  # type: ignore[arg-type]
    )

    assert result["findings"] == [expected]


def test_create_route_rejects_empty_post_build_finding(monkeypatch) -> None:
    receipt = {"schema": "receipt"}
    monkeypatch.setattr(
        routes,
        "build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda manifest: receipt,
    )
    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda candidate, manifest: [""],
    )

    with pytest.raises(HTTPException) as exc_info:
        routes.create_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
            _create_payload(), current_user=object()  # type: ignore[arg-type]
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "invalid verification receipt manifest"


@pytest.mark.parametrize("blank_finding", [" ", "\t", "\n", " \t\n "])
def test_create_route_rejects_whitespace_only_post_build_finding(
    monkeypatch, blank_finding: str
) -> None:
    receipt = {"schema": "receipt"}
    monkeypatch.setattr(
        routes,
        "build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda manifest: receipt,
    )
    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda candidate, manifest: [blank_finding],
    )

    with pytest.raises(HTTPException) as exc_info:
        routes.create_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
            _create_payload(), current_user=object()  # type: ignore[arg-type]
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "invalid verification receipt manifest"


@pytest.mark.parametrize(
    "finding",
    [
        "digest mismatch\nforged line",
        "digest\tmismatch",
        "digest\rmismatch",
        "digest\x00mismatch",
        "digest\x7fmismatch",
        "digest\x80mismatch",
        "digest\x85mismatch",
        "digest\x9bmismatch",
        "digest\x9fmismatch",
    ],
)
def test_create_route_rejects_control_character_post_build_finding(
    monkeypatch, finding: str
) -> None:
    receipt = {"schema": "receipt"}
    monkeypatch.setattr(
        routes,
        "build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda manifest: receipt,
    )
    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda candidate, manifest: [finding],
    )

    with pytest.raises(HTTPException) as exc_info:
        routes.create_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
            _create_payload(), current_user=object()  # type: ignore[arg-type]
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "invalid verification receipt manifest"


@pytest.mark.parametrize(
    "finding",
    [
        "digest\u200bmismatch",
        "digest\u2060mismatch",
        "digest\u202emismatch",
        "digest\u2066mismatch",
        "digest\ufeffmismatch",
    ],
)
def test_create_route_rejects_unicode_format_post_build_finding(
    monkeypatch, finding: str
) -> None:
    receipt = {"schema": "receipt"}
    monkeypatch.setattr(
        routes,
        "build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda manifest: receipt,
    )
    monkeypatch.setattr(
        routes,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda candidate, manifest: [finding],
    )

    with pytest.raises(HTTPException) as exc_info:
        routes.create_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
            _create_payload(), current_user=object()  # type: ignore[arg-type]
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "invalid verification receipt manifest"
