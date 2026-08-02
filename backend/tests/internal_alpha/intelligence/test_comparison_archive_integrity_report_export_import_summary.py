import hashlib

import pytest

from app.internal_alpha.intelligence import comparison_archive_integrity_report_export_bundle as bundles


def _valid_bundle(monkeypatch) -> dict[str, object]:
    report = {"schema": "report", "integrity_report_sha256": "c" * 64}
    receipt = {"verification_receipt_manifest_verification_receipt_sha256": "b" * 64}
    manifest = {"verification_receipt_manifest_sha256": "a" * 64, "entry_count": 3}
    monkeypatch.setattr(
        bundles,
        "validate_intelligence_comparison_archive_integrity_report",
        lambda candidate_report, candidate_receipt, candidate_manifest: [],
    )
    return bundles.build_intelligence_comparison_archive_integrity_report_export_bundle(
        report,
        receipt,
        manifest,
    )


def test_import_summary_binds_exact_canonical_bytes(monkeypatch) -> None:
    bundle = _valid_bundle(monkeypatch)
    payload = bundles.serialize_intelligence_comparison_archive_integrity_report_export_bundle(bundle)

    first = bundles.summarize_intelligence_comparison_archive_integrity_report_export_import(
        payload
    )
    second = bundles.summarize_intelligence_comparison_archive_integrity_report_export_import(
        payload
    )

    assert first == second
    assert first["bundle"] == bundle
    assert first["canonical_byte_count"] == len(payload)
    assert first["canonical_payload_sha256"] == hashlib.sha256(payload).hexdigest()
    assert first["export_bundle_sha256"] == bundle["export_bundle_sha256"]
    assert "does not authorize" in first["interpretation_notice"]


def test_import_summary_preserves_fail_closed_deserialization(monkeypatch) -> None:
    monkeypatch.setattr(
        bundles,
        "deserialize_intelligence_comparison_archive_integrity_report_export_bundle",
        lambda payload: (_ for _ in ()).throw(ValueError("payload is not canonical JSON")),
    )

    with pytest.raises(ValueError, match="not canonical JSON"):
        bundles.summarize_intelligence_comparison_archive_integrity_report_export_import(
            b'{"bundle":true}'
        )
