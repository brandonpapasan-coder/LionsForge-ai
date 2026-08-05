import copy

import pytest

from app.internal_alpha.intelligence import (
    comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt as subject,
)


def _ledger() -> dict[str, object]:
    return {
        "schema": "ledger-schema",
        "schema_version": 1,
        "entry_count": 2,
        "entries": [],
        "verification_state": "VERIFIED",
        "interpretation_notice": "ledger notice",
        "ledger_sha256": "a" * 64,
    }


def _accept_ledger(ledger: dict[str, object]) -> list[str]:
    del ledger
    return []


def test_build_receipt_binds_exact_ledger(monkeypatch) -> None:
    ledger = _ledger()
    seen: list[dict[str, object]] = []

    def fake_validate(payload: dict[str, object]) -> list[str]:
        seen.append(payload)
        return []

    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger",
        fake_validate,
    )

    receipt = subject.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt(
        ledger
    )

    assert seen == [ledger]
    assert receipt["ledger_sha256"] == ledger["ledger_sha256"]
    assert receipt["entry_count"] == ledger["entry_count"]
    assert receipt["verification_state"] == "VERIFIED"
    assert len(receipt["ledger_receipt_sha256"]) == 64
    assert "does not infer causality" in receipt["interpretation_notice"]


def test_build_receipt_rejects_invalid_ledger(monkeypatch) -> None:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger",
        lambda ledger: ["bundle receipt ledger digest mismatch"],
    )

    with pytest.raises(ValueError, match="bundle receipt ledger digest mismatch"):
        subject.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt(
            _ledger()
        )


def test_validate_receipt_accepts_exact_binding(monkeypatch) -> None:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger",
        _accept_ledger,
    )
    ledger = _ledger()
    receipt = subject.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt(
        ledger
    )

    assert (
        subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt(
            receipt,
            ledger,
        )
        == []
    )


def test_validate_receipt_rejects_ledger_substitution(monkeypatch) -> None:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger",
        _accept_ledger,
    )
    ledger = _ledger()
    receipt = subject.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt(
        ledger
    )
    substituted = copy.deepcopy(ledger)
    substituted["ledger_sha256"] = "b" * 64

    findings = subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt(
        receipt,
        substituted,
    )

    assert "comparison archive bundle receipt ledger receipt ledger_sha256 mismatch" in findings
    assert "comparison archive bundle receipt ledger receipt digest mismatch" in findings


def test_validate_receipt_rejects_receipt_drift(monkeypatch) -> None:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger",
        _accept_ledger,
    )
    ledger = _ledger()
    receipt = subject.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt(
        ledger
    )
    receipt["entry_count"] = 3

    findings = subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt(
        receipt,
        ledger,
    )

    assert "comparison archive bundle receipt ledger receipt entry_count mismatch" in findings


def test_validate_receipt_preserves_ledger_findings(monkeypatch) -> None:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger",
        lambda ledger: ["bundle receipt ledger ordering invalid"],
    )

    findings = subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt(
        {},
        _ledger(),
    )

    assert "bundle receipt ledger ordering invalid" in findings


def test_validate_receipt_rejects_coercive_schema_and_count(monkeypatch) -> None:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger",
        _accept_ledger,
    )
    ledger = _ledger()
    receipt = subject.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt(
        ledger
    )
    receipt["schema_version"] = True
    receipt["entry_count"] = True

    findings = subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt(
        receipt,
        ledger,
    )

    assert "comparison archive bundle receipt ledger receipt schema version mismatch" in findings
    assert "comparison archive bundle receipt ledger receipt entry_count invalid" in findings


def test_validate_receipt_rejects_malformed_ledger_binding(monkeypatch) -> None:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger",
        _accept_ledger,
    )
    ledger = _ledger()
    receipt = subject.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt(
        ledger
    )
    receipt["ledger_sha256"] = "A" * 64

    findings = subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt(
        receipt,
        ledger,
    )

    assert "comparison archive bundle receipt ledger receipt ledger_sha256 invalid" in findings
    assert "comparison archive bundle receipt ledger receipt ledger_sha256 mismatch" not in findings


def test_validate_receipt_distinguishes_malformed_receipt_digest(monkeypatch) -> None:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger",
        _accept_ledger,
    )
    ledger = _ledger()
    receipt = subject.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt(
        ledger
    )
    receipt["ledger_receipt_sha256"] = "not-a-digest"

    findings = subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt(
        receipt,
        ledger,
    )

    assert "comparison archive bundle receipt ledger receipt digest invalid" in findings
    assert "comparison archive bundle receipt ledger receipt digest mismatch" not in findings


def test_validate_receipt_rejects_non_object_and_invalid_binding(monkeypatch) -> None:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger",
        _accept_ledger,
    )

    findings = subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt(
        [],
        _ledger(),
    )
    assert "comparison archive bundle receipt ledger receipt must be an object" in findings

    ledger = _ledger()
    del ledger["ledger_sha256"]
    findings = subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt(
        {},
        ledger,
    )
    assert "comparison archive bundle receipt ledger receipt binding invalid" in findings
