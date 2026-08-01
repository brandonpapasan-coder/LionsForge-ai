import copy

import pytest

from app.internal_alpha.intelligence import (
    comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt as subject,
)


def _manifest() -> dict[str, object]:
    return {
        "schema": "manifest-schema",
        "schema_version": 1,
        "entry_count": 2,
        "entries": [],
        "verification_state": "VERIFIED",
        "interpretation_notice": "manifest notice",
        "manifest_sha256": "a" * 64,
    }


def test_build_receipt_binds_exact_manifest(monkeypatch) -> None:
    manifest = _manifest()
    seen: list[dict[str, object]] = []

    def fake_validate(payload: dict[str, object]) -> list[str]:
        seen.append(payload)
        return []

    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest",
        fake_validate,
    )

    receipt = subject.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt(
        manifest
    )

    assert seen == [manifest]
    assert receipt["manifest_sha256"] == manifest["manifest_sha256"]
    assert receipt["entry_count"] == manifest["entry_count"]
    assert receipt["verification_state"] == "VERIFIED"
    assert len(receipt["manifest_verification_receipt_sha256"]) == 64
    assert "does not infer causality" in receipt["interpretation_notice"]


def test_build_receipt_is_deterministic(monkeypatch) -> None:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest",
        lambda manifest: [],
    )
    manifest = _manifest()

    first = subject.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt(
        manifest
    )
    second = subject.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt(
        copy.deepcopy(manifest)
    )

    assert first == second


def test_build_receipt_rejects_invalid_manifest(monkeypatch) -> None:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest",
        lambda manifest: ["ledger receipt manifest digest mismatch"],
    )

    with pytest.raises(ValueError, match="ledger receipt manifest digest mismatch"):
        subject.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt(
            _manifest()
        )


def test_validate_receipt_accepts_exact_binding(monkeypatch) -> None:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest",
        lambda manifest: [],
    )
    manifest = _manifest()
    receipt = subject.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt(
        manifest
    )

    assert (
        subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt(
            receipt,
            manifest,
        )
        == []
    )


def test_validate_receipt_rejects_manifest_substitution(monkeypatch) -> None:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest",
        lambda manifest: [],
    )
    manifest = _manifest()
    receipt = subject.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt(
        manifest
    )
    substituted = copy.deepcopy(manifest)
    substituted["manifest_sha256"] = "b" * 64

    findings = subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt(
        receipt,
        substituted,
    )

    assert "ledger receipt manifest verification receipt manifest_sha256 mismatch" in findings
    assert "ledger receipt manifest verification receipt digest mismatch" in findings


def test_validate_receipt_rejects_receipt_drift(monkeypatch) -> None:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest",
        lambda manifest: [],
    )
    manifest = _manifest()
    receipt = subject.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt(
        manifest
    )
    receipt["entry_count"] = 3

    findings = subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt(
        receipt,
        manifest,
    )

    assert "ledger receipt manifest verification receipt entry_count mismatch" in findings
    assert "ledger receipt manifest verification receipt digest mismatch" in findings


def test_validate_receipt_preserves_manifest_findings(monkeypatch) -> None:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest",
        lambda manifest: ["ledger receipt manifest entries not canonically ordered"],
    )

    findings = subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt(
        {},
        _manifest(),
    )

    assert "ledger receipt manifest entries not canonically ordered" in findings
    assert "ledger receipt manifest verification receipt keys invalid" in findings


def test_validate_receipt_rejects_non_object_receipt(monkeypatch) -> None:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest",
        lambda manifest: [],
    )

    findings = subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt(
        [],  # type: ignore[arg-type]
        _manifest(),
    )

    assert findings == ["ledger receipt manifest verification receipt must be an object"]
