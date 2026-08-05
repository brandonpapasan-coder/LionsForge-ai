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


def _accept_manifest(manifest: dict[str, object]) -> list[str]:
    del manifest
    return []


def _receipt(monkeypatch) -> tuple[dict[str, object], dict[str, object]]:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest",
        _accept_manifest,
    )
    manifest = _manifest()
    receipt = subject.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt(
        manifest
    )
    return manifest, receipt


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
        _accept_manifest,
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
    manifest, receipt = _receipt(monkeypatch)

    assert (
        subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt(
            receipt,
            manifest,
        )
        == []
    )


def test_validate_receipt_rejects_manifest_substitution(monkeypatch) -> None:
    manifest, receipt = _receipt(monkeypatch)
    substituted = copy.deepcopy(manifest)
    substituted["manifest_sha256"] = "b" * 64

    findings = subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt(
        receipt,
        substituted,
    )

    assert "ledger receipt manifest verification receipt manifest_sha256 mismatch" in findings
    assert "ledger receipt manifest verification receipt digest mismatch" in findings


def test_validate_receipt_rejects_receipt_drift(monkeypatch) -> None:
    manifest, receipt = _receipt(monkeypatch)
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
        _accept_manifest,
    )

    findings = subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt(
        [],  # type: ignore[arg-type]
        _manifest(),
    )

    assert findings == ["ledger receipt manifest verification receipt must be an object"]


def test_validate_receipt_rejects_invalid_manifest_binding(monkeypatch) -> None:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest",
        _accept_manifest,
    )

    findings = subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt(
        {},
        {},
    )

    assert "ledger receipt manifest verification receipt binding invalid" in findings


@pytest.mark.parametrize("value", [True, 1.0, "1"])
def test_validate_receipt_rejects_coercive_schema_versions(monkeypatch, value: object) -> None:
    manifest, receipt = _receipt(monkeypatch)
    receipt["schema_version"] = value

    findings = subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt(
        receipt,
        manifest,
    )

    assert "ledger receipt manifest verification receipt schema version mismatch" in findings
    assert "ledger receipt manifest verification receipt digest mismatch" in findings


@pytest.mark.parametrize("value", [True, 2.0, "2"])
def test_validate_receipt_rejects_coercive_entry_counts(monkeypatch, value: object) -> None:
    manifest, receipt = _receipt(monkeypatch)
    receipt["entry_count"] = value

    findings = subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt(
        receipt,
        manifest,
    )

    assert "ledger receipt manifest verification receipt entry_count invalid" in findings
    assert "ledger receipt manifest verification receipt digest mismatch" in findings


@pytest.mark.parametrize("value", ["A" * 64, "not-a-digest", "a" * 63])
def test_validate_receipt_rejects_malformed_manifest_digests(monkeypatch, value: object) -> None:
    manifest, receipt = _receipt(monkeypatch)
    receipt["manifest_sha256"] = value

    findings = subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt(
        receipt,
        manifest,
    )

    assert "ledger receipt manifest verification receipt manifest_sha256 invalid" in findings
    assert "ledger receipt manifest verification receipt digest mismatch" in findings


@pytest.mark.parametrize("value", ["A" * 64, "not-a-digest", "a" * 63, None])
def test_validate_receipt_distinguishes_malformed_receipt_digest(monkeypatch, value: object) -> None:
    manifest, receipt = _receipt(monkeypatch)
    receipt["manifest_verification_receipt_sha256"] = value

    findings = subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt(
        receipt,
        manifest,
    )

    assert "ledger receipt manifest verification receipt digest invalid" in findings
    assert "ledger receipt manifest verification receipt digest mismatch" not in findings


def test_validate_receipt_rejects_valid_but_wrong_receipt_digest(monkeypatch) -> None:
    manifest, receipt = _receipt(monkeypatch)
    receipt["manifest_verification_receipt_sha256"] = "b" * 64

    findings = subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt(
        receipt,
        manifest,
    )

    assert "ledger receipt manifest verification receipt digest mismatch" in findings
    assert "ledger receipt manifest verification receipt digest invalid" not in findings
