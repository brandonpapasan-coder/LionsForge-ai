from copy import deepcopy
import hashlib

from app.internal_alpha.intelligence import (
    comparison_archive_integrity_report_export_import_summary as summaries,
)


def _summary() -> dict[str, object]:
    bundle = {"export_bundle_sha256": "a" * 64}
    payload = b'{"bundle":true}'
    return {
        "bundle": bundle,
        "canonical_byte_count": len(payload),
        "canonical_payload_sha256": hashlib.sha256(payload).hexdigest(),
        "export_bundle_sha256": "a" * 64,
        "interpretation_notice": summaries._SUMMARY_NOTICE,
    }


def test_validator_reconstructs_exact_transport_metadata(monkeypatch) -> None:
    summary = _summary()
    monkeypatch.setattr(
        summaries,
        "validate_intelligence_comparison_archive_integrity_report_export_bundle",
        lambda candidate_bundle: [],
    )
    monkeypatch.setattr(
        summaries,
        "serialize_intelligence_comparison_archive_integrity_report_export_bundle",
        lambda candidate_bundle: b'{"bundle":true}',
    )
    assert (
        summaries.validate_intelligence_comparison_archive_integrity_report_export_import_summary(
            summary
        )
        == []
    )


def test_validator_detects_each_summary_metadata_mismatch(monkeypatch) -> None:
    monkeypatch.setattr(
        summaries,
        "validate_intelligence_comparison_archive_integrity_report_export_bundle",
        lambda candidate_bundle: [],
    )
    monkeypatch.setattr(
        summaries,
        "serialize_intelligence_comparison_archive_integrity_report_export_bundle",
        lambda candidate_bundle: b'{"bundle":true}',
    )
    cases = {
        "canonical_byte_count": 1,
        "canonical_payload_sha256": "b" * 64,
        "export_bundle_sha256": "c" * 64,
        "interpretation_notice": "changed",
    }
    for field, value in cases.items():
        candidate = deepcopy(_summary())
        candidate[field] = value
        findings = (
            summaries.validate_intelligence_comparison_archive_integrity_report_export_import_summary(
                candidate
            )
        )
        assert any(field in finding for finding in findings)


def test_validator_rejects_non_integer_byte_count(monkeypatch) -> None:
    candidate = _summary()
    candidate["canonical_byte_count"] = True
    monkeypatch.setattr(
        summaries,
        "validate_intelligence_comparison_archive_integrity_report_export_bundle",
        lambda candidate_bundle: [],
    )
    monkeypatch.setattr(
        summaries,
        "serialize_intelligence_comparison_archive_integrity_report_export_bundle",
        lambda candidate_bundle: b'{"bundle":true}',
    )
    findings = summaries.validate_intelligence_comparison_archive_integrity_report_export_import_summary(
        candidate
    )
    assert "integrity report export import summary canonical_byte_count invalid" in findings


def test_validator_preserves_embedded_bundle_findings(monkeypatch) -> None:
    monkeypatch.setattr(
        summaries,
        "validate_intelligence_comparison_archive_integrity_report_export_bundle",
        lambda candidate_bundle: ["embedded bundle digest mismatch"],
    )
    findings = summaries.validate_intelligence_comparison_archive_integrity_report_export_import_summary(
        _summary()
    )
    assert findings == ["embedded bundle digest mismatch"]


def test_validator_rejects_invalid_shape() -> None:
    assert summaries.validate_intelligence_comparison_archive_integrity_report_export_import_summary(
        []  # type: ignore[arg-type]
    ) == ["integrity report export import summary must be an object"]
    candidate = _summary()
    candidate["extra"] = True
    findings = summaries.validate_intelligence_comparison_archive_integrity_report_export_import_summary(
        candidate
    )
    assert "integrity report export import summary keys invalid" in findings
    candidate["bundle"] = []
    findings = summaries.validate_intelligence_comparison_archive_integrity_report_export_import_summary(
        candidate
    )
    assert "integrity report export import summary bundle must be an object" in findings
