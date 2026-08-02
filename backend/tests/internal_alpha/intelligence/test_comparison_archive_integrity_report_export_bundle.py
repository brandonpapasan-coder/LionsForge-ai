from copy import deepcopy

import pytest

from app.internal_alpha.intelligence import comparison_archive_integrity_report_export_bundle as bundles


def _source() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    report = {"schema": "report", "integrity_report_sha256": "c" * 64}
    receipt = {"verification_receipt_manifest_verification_receipt_sha256": "b" * 64}
    manifest = {"verification_receipt_manifest_sha256": "a" * 64, "entry_count": 3}
    return report, receipt, manifest


def _valid_bundle(monkeypatch) -> dict[str, object]:
    report, receipt, manifest = _source()
    monkeypatch.setattr(
        bundles,
        "validate_intelligence_comparison_archive_integrity_report",
        lambda candidate_report, candidate_receipt, candidate_manifest: [],
    )
    return bundles.build_intelligence_comparison_archive_integrity_report_export_bundle(
        report, receipt, manifest
    )


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
        lambda candidate_report, candidate_receipt, candidate_manifest: ["integrity report digest mismatch"],
    )
    with pytest.raises(ValueError, match="integrity report digest mismatch"):
        bundles.build_intelligence_comparison_archive_integrity_report_export_bundle(
            report, receipt, manifest
        )


def test_validator_detects_notice_and_digest_tampering(monkeypatch) -> None:
    tampered = deepcopy(_valid_bundle(monkeypatch))
    tampered["interpretation_notice"] = "changed"
    findings = bundles.validate_intelligence_comparison_archive_integrity_report_export_bundle(
        tampered
    )
    assert "integrity report export bundle interpretation_notice mismatch" in findings
    assert "integrity report export bundle digest mismatch" in findings


def test_validator_preserves_nested_source_findings(monkeypatch) -> None:
    bundle = _valid_bundle(monkeypatch)
    bundle["receipt"] = {"replacement": True}
    monkeypatch.setattr(
        bundles,
        "validate_intelligence_comparison_archive_integrity_report",
        lambda candidate_report, candidate_receipt, candidate_manifest: ["source receipt invalid"],
    )
    findings = bundles.validate_intelligence_comparison_archive_integrity_report_export_bundle(
        bundle
    )
    assert findings[0] == "source receipt invalid"
    assert "integrity report export bundle digest mismatch" in findings


def test_validator_rejects_non_object_extra_keys_and_malformed_nested_objects(monkeypatch) -> None:
    assert bundles.validate_intelligence_comparison_archive_integrity_report_export_bundle(
        []  # type: ignore[arg-type]
    ) == ["integrity report export bundle must be an object"]
    bundle = _valid_bundle(monkeypatch)
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


def test_serialization_is_canonical_and_round_trips(monkeypatch) -> None:
    bundle = _valid_bundle(monkeypatch)
    payload = bundles.serialize_intelligence_comparison_archive_integrity_report_export_bundle(bundle)
    assert payload == bundles.serialize_intelligence_comparison_archive_integrity_report_export_bundle(
        dict(reversed(list(bundle.items())))
    )
    assert payload.endswith(b"}")
    assert bundles.deserialize_intelligence_comparison_archive_integrity_report_export_bundle(
        payload
    ) == bundle


def test_serialization_rejects_tampering_and_deserialization_rejects_bad_bytes(monkeypatch) -> None:
    bundle = _valid_bundle(monkeypatch)
    bundle["schema_version"] = 2
    with pytest.raises(ValueError, match="schema_version mismatch"):
        bundles.serialize_intelligence_comparison_archive_integrity_report_export_bundle(bundle)
    for payload in (b"", b"not-json", b"[]", b"\xff"):
        with pytest.raises(ValueError):
            bundles.deserialize_intelligence_comparison_archive_integrity_report_export_bundle(payload)
    with pytest.raises(TypeError):
        bundles.deserialize_intelligence_comparison_archive_integrity_report_export_bundle(  # type: ignore[arg-type]
            "{}"
        )


def test_deserialization_enforces_byte_limit() -> None:
    with pytest.raises(ValueError, match="exceeds byte limit"):
        bundles.deserialize_intelligence_comparison_archive_integrity_report_export_bundle(
            b"x" * (bundles._MAX_EXPORT_BYTES + 1)
        )
