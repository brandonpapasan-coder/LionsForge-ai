from copy import deepcopy

import pytest

from app.internal_alpha.intelligence import comparison_archive_receipt_manifest_bundle_receipt as subject


def _bundle(seed: str = "a") -> dict[str, object]:
    return {
        "bundle_sha256": seed * 64,
        "manifest_sha256": "b" * 64,
        "receipt_sha256": "c" * 64,
        "entry_count": 2,
    }


def test_build_bundle_receipt_is_deterministic(monkeypatch) -> None:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle",
        lambda bundle: [],
    )
    bundle = _bundle()

    first = subject.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt(bundle)
    second = subject.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt(bundle)

    assert first == second
    assert first["bundle_sha256"] == bundle["bundle_sha256"]
    assert first["manifest_sha256"] == bundle["manifest_sha256"]
    assert first["receipt_sha256"] == bundle["receipt_sha256"]
    assert first["entry_count"] == bundle["entry_count"]
    assert first["verification_state"] == "VERIFIED"
    assert len(first["bundle_receipt_sha256"]) == 64


def test_build_bundle_receipt_rejects_invalid_bundle(monkeypatch) -> None:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle",
        lambda bundle: ["comparison archive receipt manifest bundle digest mismatch"],
    )

    with pytest.raises(ValueError, match="invalid comparison archive receipt manifest bundle"):
        subject.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt(_bundle())


def test_validate_bundle_receipt_accepts_exact_binding(monkeypatch) -> None:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle",
        lambda bundle: [],
    )
    bundle = _bundle()
    receipt = subject.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt(bundle)

    assert (
        subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt(
            receipt,
            bundle,
        )
        == []
    )


def test_validate_bundle_receipt_detects_field_and_digest_drift(monkeypatch) -> None:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle",
        lambda bundle: [],
    )
    bundle = _bundle()
    receipt = subject.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt(bundle)
    drifted = deepcopy(receipt)
    drifted["entry_count"] = 3
    drifted["bundle_receipt_sha256"] = "0" * 64

    findings = subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt(
        drifted,
        bundle,
    )

    assert "comparison archive receipt manifest bundle receipt entry_count mismatch" in findings
    assert "comparison archive receipt manifest bundle receipt digest mismatch" in findings


def test_validate_bundle_receipt_detects_bundle_substitution(monkeypatch) -> None:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle",
        lambda bundle: [],
    )
    original = _bundle("a")
    substituted = _bundle("d")
    receipt = subject.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt(original)

    findings = subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt(
        receipt,
        substituted,
    )

    assert "comparison archive receipt manifest bundle receipt bundle_sha256 mismatch" in findings
    assert "comparison archive receipt manifest bundle receipt digest mismatch" in findings


def test_validate_bundle_receipt_rejects_coercive_schema_version_and_count(monkeypatch) -> None:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle",
        lambda bundle: [],
    )
    bundle = _bundle()
    receipt = subject.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt(bundle)
    receipt["schema_version"] = True
    receipt["entry_count"] = True

    findings = subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt(
        receipt,
        bundle,
    )

    assert "comparison archive receipt manifest bundle receipt schema version mismatch" in findings
    assert "comparison archive receipt manifest bundle receipt entry_count mismatch" in findings


def test_validate_bundle_receipt_rejects_malformed_digests(monkeypatch) -> None:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle",
        lambda bundle: [],
    )
    bundle = _bundle()
    receipt = subject.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt(bundle)
    receipt["bundle_sha256"] = "A" * 64
    receipt["manifest_sha256"] = "not-a-digest"
    receipt["receipt_sha256"] = "C" * 64
    receipt["bundle_receipt_sha256"] = "B" * 64

    findings = subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt(
        receipt,
        bundle,
    )

    assert "comparison archive receipt manifest bundle receipt bundle_sha256 invalid" in findings
    assert "comparison archive receipt manifest bundle receipt manifest_sha256 invalid" in findings
    assert "comparison archive receipt manifest bundle receipt receipt_sha256 invalid" in findings
    assert "comparison archive receipt manifest bundle receipt digest invalid" in findings
    assert "comparison archive receipt manifest bundle receipt bundle_sha256 mismatch" not in findings
    assert "comparison archive receipt manifest bundle receipt manifest_sha256 mismatch" not in findings
    assert "comparison archive receipt manifest bundle receipt receipt_sha256 mismatch" not in findings
    assert "comparison archive receipt manifest bundle receipt digest mismatch" not in findings


def test_validate_bundle_receipt_rejects_unexpected_keys(monkeypatch) -> None:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle",
        lambda bundle: [],
    )
    bundle = _bundle()
    receipt = subject.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt(bundle)
    receipt["unexpected"] = True

    findings = subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt(
        receipt,
        bundle,
    )

    assert "comparison archive receipt manifest bundle receipt keys invalid" in findings


def test_validate_bundle_receipt_fails_closed_for_malformed_values(monkeypatch) -> None:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle",
        lambda bundle: ["comparison archive receipt manifest bundle must be an object"]
        if not isinstance(bundle, dict)
        else [],
    )

    findings = subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt(
        [],  # type: ignore[arg-type]
        {},
    )

    assert "comparison archive receipt manifest bundle receipt must be an object" in findings
