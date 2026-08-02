from copy import deepcopy

import pytest

from app.internal_alpha.intelligence import comparison_archive_integrity_report_export_bundle as bundles


def _source() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    report = {
        "schema": "report",
        "integrity_report_sha256": "c" * 64,
    }
    receipt = {
        "verification_receipt_manifest_verification_receipt_sha256": "b" * 64,
    }
    manifest = {
        "verification_receipt_manifest_sha256": "a" * 64,
        "entry_count": 3,
    }
    return report, receipt, manifest


def test_export_bundle_is_deterministic_and_self_contained(monkeypatch) -> None:
    report, receipt, manifest = _source()
    monkeypatch.setattr(
        bundles,
        "validate_intelligence_comparison_archive_integrity_report",
        lambda candidate_report, candidate_receipt, candidate_manifest: [],
    )

    first = bundles.build_intelligence_comparison_archive_integrity_report_export_bundle(
        report, receipt, manifest
    )
    second = bundles.build_intelligence_comparison_archive_integrity_report_export_bundle(
        report, receipt, manifest
    )

    assert first == second
    assert first["report"] == report
    assert first["receipt"] == receipt
    assert first["manifest"] == manifest
    assert len(first["export_bundle_sha256"]) == 64
    assert bundles.validate_intelligence_comparison_archive_integrity_report_export_bundle(first) == []


def test_builder_rejects_invalid_source_chain(monkeypatch) -> None:
    report, receipt, manifest = _source()
    monkeypatch.setattr(
        bundles,
        "validate_intelligence_comparison_archive_integrity_report",
        lambda candidate_report, candidate_receipt, candidate_manifest: [
            "integrity report digest mismatch"
        ],
    )

    with pytest.raises(ValueError, match="integrity report digest mismatch"):
        bundles.build_intelligence_comparison_archive_integrity_report_export_bundle(
            report, receipt, manifest
        )


def test_validator_detects_notice_and_digest_tampering(monkeypatch) -> None:
    report, receipt, manifest = _source()
    monkeypatch.setattr(
        bundles,
        "validate_intelligence_comparison_archive_integrity_report",
        lambda candidate_report, candidate_receipt, candidate_manifest: [],
    )
    bundle = bundles.build_intelligence_comparison_archive_integrity_report_export_bundle(
        report, receipt, manifest
    )
    tampered = deepcopy(bundle)
    tampered["interpretation_notice"] = "changed"

    findings = bundles.validate_intelligence_comparison_archive_integrity_report_export_bundle(
        tampered
    )

    assert "integrity report export bundle interpretation_notice mismatch" in findings
    assert "integrity report export bundle digest mismatch" in findings


def test_validator_preserves_nested_source_findings(monkeypatch) -> None:
    report, receipt, manifest = _source()
    monkeypatch.setattr(
        bundles,
        "validate_intelligence_comparison_archive_integrity_report",
        lambda candidate_report, candidate_receipt, candidate_manifest: [],
    )
    bundle = bundles.build_intelligence_comparison_archive_integrity_report_export_bundle(
        report, receipt, manifest
    )
    bundle["receipt"] = {"replacement": True}
    monkeypatch.setattr(
        bundles,
        "validate_intelligence_comparison_archive_integrity_report",
        lambda candidate_report, candidate_receipt, candidate_manifest: [
            "source receipt invalid"
        ],
    )

    findings = bundles.validate_intelligence_comparison_archive_integrity_report_export_bundle(
        bundle
    )

    assert findings[0] == "source receipt invalid"
    assert "integrity report export bundle digest mismatch" in findings


def test_validator_rejects_non_object_extra_keys_and_malformed_nested_objects(
    monkeypatch,
) -> None:
    report, receipt, manifest = _source()
    monkeypatch.setattr(
        bundles,
        "validate_intelligence_comparison_archive_integrity_report",
        lambda candidate_report, candidate_receipt, candidate_manifest: [],
    )
    assert bundles.validate_intelligence_comparison_archive_integrity_report_export_bundle(
        []  # type: ignore[arg-type]
    ) == ["integrity report export bundle must be an object"]

    bundle = bundles.build_intelligence_comparison_archive_integrity_report_export_bundle(
        report, receipt, manifest
    )
    bundle["extra"] = True
    assert "integrity report export bundle keys invalid" in (
        bundles.validate_intelligence_comparison_archive_integrity_report_export_bundle(bundle)
    )

    malformed = deepcopy(bundle)
    malformed.pop("extra")
    malformed["manifest"] = []
    findings = bundles.validate_intelligence_comparison_archive_integrity_report_export_bundle(
        malformed
    )
    assert "integrity report export bundle manifest must be an object" in findings
