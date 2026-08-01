from copy import deepcopy

import pytest

from app.internal_alpha.intelligence import comparison_archive_receipt_manifest_bundle as bundle_module


def _manifest() -> dict:
    return {
        "manifest_sha256": "a" * 64,
        "entry_count": 2,
    }


def _receipt() -> dict:
    return {
        "receipt_sha256": "b" * 64,
    }


@pytest.fixture(autouse=True)
def valid_manifest_receipt_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        bundle_module,
        "validate_intelligence_comparison_archive_receipt_manifest_receipt",
        lambda receipt, manifest: [],
    )


def test_builds_deterministic_bundle() -> None:
    manifest = _manifest()
    receipt = _receipt()

    first = bundle_module.build_intelligence_comparison_archive_receipt_manifest_bundle(
        manifest,
        receipt,
    )
    second = bundle_module.build_intelligence_comparison_archive_receipt_manifest_bundle(
        deepcopy(manifest),
        deepcopy(receipt),
    )

    assert first == second
    assert first["manifest"] == manifest
    assert first["receipt"] == receipt
    assert first["manifest_sha256"] == "a" * 64
    assert first["receipt_sha256"] == "b" * 64
    assert first["entry_count"] == 2
    assert bundle_module.validate_intelligence_comparison_archive_receipt_manifest_bundle(first) == []


def test_rejects_invalid_manifest_receipt_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        bundle_module,
        "validate_intelligence_comparison_archive_receipt_manifest_receipt",
        lambda receipt, manifest: ["comparison archive receipt manifest receipt digest mismatch"],
    )

    with pytest.raises(ValueError, match="invalid comparison archive receipt manifest chain"):
        bundle_module.build_intelligence_comparison_archive_receipt_manifest_bundle(
            _manifest(),
            _receipt(),
        )


def test_detects_manifest_substitution_and_digest_drift() -> None:
    bundle = bundle_module.build_intelligence_comparison_archive_receipt_manifest_bundle(
        _manifest(),
        _receipt(),
    )
    drifted = deepcopy(bundle)
    drifted["manifest"]["manifest_sha256"] = "c" * 64

    findings = bundle_module.validate_intelligence_comparison_archive_receipt_manifest_bundle(
        drifted
    )

    assert "comparison archive receipt manifest bundle manifest_sha256 mismatch" in findings
    assert "comparison archive receipt manifest bundle digest mismatch" in findings


def test_detects_receipt_substitution_and_count_drift() -> None:
    bundle = bundle_module.build_intelligence_comparison_archive_receipt_manifest_bundle(
        _manifest(),
        _receipt(),
    )
    drifted = deepcopy(bundle)
    drifted["receipt"]["receipt_sha256"] = "d" * 64
    drifted["entry_count"] = 3

    findings = bundle_module.validate_intelligence_comparison_archive_receipt_manifest_bundle(
        drifted
    )

    assert "comparison archive receipt manifest bundle receipt_sha256 mismatch" in findings
    assert "comparison archive receipt manifest bundle entry_count mismatch" in findings
    assert "comparison archive receipt manifest bundle digest mismatch" in findings


def test_fails_closed_for_malformed_bundle_and_chain() -> None:
    assert bundle_module.validate_intelligence_comparison_archive_receipt_manifest_bundle([]) == [
        "comparison archive receipt manifest bundle must be an object"
    ]

    malformed = {
        "schema": "lionsforge.internal-alpha-intelligence-comparison-archive-receipt-manifest-bundle",
        "schema_version": 1,
        "manifest": [],
        "receipt": {},
        "manifest_sha256": "a" * 64,
        "receipt_sha256": "b" * 64,
        "entry_count": 2,
        "bundle_sha256": "c" * 64,
        "interpretation_notice": (
            "This bundle preserves deterministic archive receipt manifest transfer integrity only and "
            "does not infer causality or authorize any release transition."
        ),
    }

    assert bundle_module.validate_intelligence_comparison_archive_receipt_manifest_bundle(
        malformed
    ) == ["comparison archive receipt manifest bundle chain invalid"]


def test_detects_wrong_keys_schema_version_notice_and_digest() -> None:
    bundle = bundle_module.build_intelligence_comparison_archive_receipt_manifest_bundle(
        _manifest(),
        _receipt(),
    )
    drifted = deepcopy(bundle)
    drifted["extra"] = True
    drifted["schema"] = "wrong"
    drifted["schema_version"] = 2
    drifted["interpretation_notice"] = "wrong"
    drifted["bundle_sha256"] = "0" * 64

    findings = bundle_module.validate_intelligence_comparison_archive_receipt_manifest_bundle(
        drifted
    )

    assert "comparison archive receipt manifest bundle keys invalid" in findings
    assert "comparison archive receipt manifest bundle schema mismatch" in findings
    assert "comparison archive receipt manifest bundle schema version mismatch" in findings
    assert "comparison archive receipt manifest bundle interpretation_notice mismatch" in findings
    assert "comparison archive receipt manifest bundle digest mismatch" in findings
