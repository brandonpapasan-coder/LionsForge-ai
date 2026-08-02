from copy import deepcopy

import pytest

from app.internal_alpha.intelligence import comparison_archive_integrity_report as reports


def _source() -> tuple[dict[str, object], dict[str, object]]:
    manifest = {
        "verification_receipt_manifest_sha256": "a" * 64,
        "entry_count": 3,
    }
    receipt = {
        "verification_receipt_manifest_verification_receipt_sha256": "b" * 64,
    }
    return receipt, manifest


def test_report_is_deterministic_and_bound(monkeypatch) -> None:
    receipt, manifest = _source()
    monkeypatch.setattr(
        reports,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda candidate_receipt, candidate_manifest: [],
    )

    first = reports.build_intelligence_comparison_archive_integrity_report(receipt, manifest)
    second = reports.build_intelligence_comparison_archive_integrity_report(receipt, manifest)

    assert first == second
    assert first["source_manifest_sha256"] == "a" * 64
    assert first["source_receipt_sha256"] == "b" * 64
    assert first["verified_entry_count"] == 3
    assert first["finding_count"] == 0
    assert first["integrity_state"] == "VERIFIED"
    assert len(first["integrity_report_sha256"]) == 64


def test_builder_rejects_invalid_source(monkeypatch) -> None:
    receipt, manifest = _source()
    monkeypatch.setattr(
        reports,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda candidate_receipt, candidate_manifest: ["source digest mismatch"],
    )

    with pytest.raises(ValueError, match="source digest mismatch"):
        reports.build_intelligence_comparison_archive_integrity_report(receipt, manifest)


def test_validator_detects_field_and_digest_tampering(monkeypatch) -> None:
    receipt, manifest = _source()
    monkeypatch.setattr(
        reports,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda candidate_receipt, candidate_manifest: [],
    )
    report = reports.build_intelligence_comparison_archive_integrity_report(receipt, manifest)
    tampered = deepcopy(report)
    tampered["verified_entry_count"] = 4

    findings = reports.validate_intelligence_comparison_archive_integrity_report(
        tampered,
        receipt,
        manifest,
    )

    assert "integrity report verified_entry_count mismatch" in findings
    assert "integrity report digest mismatch" in findings


def test_validator_preserves_source_findings(monkeypatch) -> None:
    receipt, manifest = _source()
    monkeypatch.setattr(
        reports,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda candidate_receipt, candidate_manifest: ["source receipt invalid"],
    )
    report = {
        "schema": "wrong",
        "schema_version": 1,
        "source_manifest_sha256": "a" * 64,
        "source_receipt_sha256": "b" * 64,
        "verified_entry_count": 3,
        "integrity_state": "VERIFIED",
        "finding_count": 0,
        "interpretation_notice": "wrong",
        "integrity_report_sha256": "c" * 64,
    }

    findings = reports.validate_intelligence_comparison_archive_integrity_report(
        report,
        receipt,
        manifest,
    )

    assert findings[0] == "source receipt invalid"
    assert "integrity report schema mismatch" in findings
    assert "integrity report interpretation_notice mismatch" in findings


def test_validator_rejects_non_object_and_extra_keys(monkeypatch) -> None:
    receipt, manifest = _source()
    monkeypatch.setattr(
        reports,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt",
        lambda candidate_receipt, candidate_manifest: [],
    )
    assert reports.validate_intelligence_comparison_archive_integrity_report(
        [], receipt, manifest  # type: ignore[arg-type]
    ) == ["integrity report must be an object"]

    report = reports.build_intelligence_comparison_archive_integrity_report(receipt, manifest)
    report["extra"] = True
    findings = reports.validate_intelligence_comparison_archive_integrity_report(
        report,
        receipt,
        manifest,
    )
    assert "integrity report keys invalid" in findings
