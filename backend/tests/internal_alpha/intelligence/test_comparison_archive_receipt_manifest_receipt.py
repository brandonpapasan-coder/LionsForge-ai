from copy import deepcopy

import pytest

from app.internal_alpha.intelligence import (
    comparison_archive_receipt_manifest_receipt as receipt_module,
)


def _manifest() -> dict:
    return {
        "schema": "lionsforge.internal-alpha-intelligence-comparison-archive-receipt-manifest",
        "schema_version": 1,
        "entry_count": 2,
        "entries": [],
        "manifest_sha256": "a" * 64,
        "interpretation_notice": "bounded evidence only",
    }


@pytest.fixture(autouse=True)
def valid_manifest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        receipt_module,
        "validate_intelligence_comparison_archive_receipt_manifest",
        lambda manifest: [],
    )


def test_builds_deterministic_manifest_receipt() -> None:
    manifest = _manifest()

    first = receipt_module.build_intelligence_comparison_archive_receipt_manifest_receipt(
        manifest
    )
    second = receipt_module.build_intelligence_comparison_archive_receipt_manifest_receipt(
        deepcopy(manifest)
    )

    assert first == second
    assert first["manifest_sha256"] == manifest["manifest_sha256"]
    assert first["entry_count"] == 2
    assert first["verification_state"] == "VERIFIED"
    assert (
        receipt_module.validate_intelligence_comparison_archive_receipt_manifest_receipt(
            first, manifest
        )
        == []
    )


def test_rejects_invalid_manifest_before_issuance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        receipt_module,
        "validate_intelligence_comparison_archive_receipt_manifest",
        lambda manifest: ["comparison archive receipt manifest digest mismatch"],
    )

    with pytest.raises(ValueError, match="invalid comparison archive receipt manifest"):
        receipt_module.build_intelligence_comparison_archive_receipt_manifest_receipt(
            _manifest()
        )


def test_detects_manifest_digest_and_entry_count_substitution() -> None:
    manifest = _manifest()
    receipt = receipt_module.build_intelligence_comparison_archive_receipt_manifest_receipt(
        manifest
    )
    drifted_manifest = deepcopy(manifest)
    drifted_manifest["manifest_sha256"] = "b" * 64
    drifted_manifest["entry_count"] = 3

    findings = (
        receipt_module.validate_intelligence_comparison_archive_receipt_manifest_receipt(
            receipt, drifted_manifest
        )
    )

    assert "comparison archive receipt manifest receipt manifest_sha256 mismatch" in findings
    assert "comparison archive receipt manifest receipt entry_count mismatch" in findings
    assert "comparison archive receipt manifest receipt digest mismatch" in findings


def test_detects_receipt_digest_and_field_drift() -> None:
    manifest = _manifest()
    receipt = receipt_module.build_intelligence_comparison_archive_receipt_manifest_receipt(
        manifest
    )
    drifted = deepcopy(receipt)
    drifted["verification_state"] = "UNVERIFIED"
    drifted["receipt_sha256"] = "0" * 64

    findings = (
        receipt_module.validate_intelligence_comparison_archive_receipt_manifest_receipt(
            drifted, manifest
        )
    )

    assert "comparison archive receipt manifest receipt verification_state mismatch" in findings
    assert "comparison archive receipt manifest receipt digest mismatch" in findings


def test_fails_closed_for_malformed_receipt_and_binding() -> None:
    manifest = _manifest()

    assert receipt_module.validate_intelligence_comparison_archive_receipt_manifest_receipt(
        [], manifest
    ) == ["comparison archive receipt manifest receipt must be an object"]

    malformed_manifest = deepcopy(manifest)
    malformed_manifest.pop("manifest_sha256")
    findings = receipt_module.validate_intelligence_comparison_archive_receipt_manifest_receipt(
        {}, malformed_manifest
    )

    assert "comparison archive receipt manifest receipt keys invalid" in findings
    assert "comparison archive receipt manifest receipt binding invalid" in findings
