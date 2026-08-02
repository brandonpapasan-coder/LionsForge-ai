from copy import deepcopy

import pytest

from app.internal_alpha.intelligence import (
    comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt as subject,
)


def _manifest() -> dict:
    return {
        "schema": "source-schema",
        "schema_version": 1,
        "entry_count": 2,
        "entries": [{"receipt": {}, "manifest": {}}],
        "verification_state": "VERIFIED",
        "interpretation_notice": "source notice",
        "verification_receipt_manifest_sha256": "a" * 64,
    }


def test_build_is_deterministic_and_binds_source(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest",
        lambda manifest: [],
    )
    manifest = _manifest()

    first = subject.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt(
        manifest
    )
    second = subject.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt(
        deepcopy(manifest)
    )

    assert first == second
    assert first["verification_receipt_manifest_sha256"] == "a" * 64
    assert first["entry_count"] == 2
    assert first["verification_state"] == "VERIFIED"
    assert len(first["verification_receipt_manifest_verification_receipt_sha256"]) == 64


def test_build_rejects_invalid_source(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest",
        lambda manifest: ["source invalid"],
    )

    with pytest.raises(ValueError, match="invalid verification receipt manifest: source invalid"):
        subject.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt(
            _manifest()
        )


def test_validate_accepts_exact_receipt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest",
        lambda manifest: [],
    )
    manifest = _manifest()
    receipt = subject.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt(
        manifest
    )

    assert (
        subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt(
            receipt,
            manifest,
        )
        == []
    )


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        (
            "verification_receipt_manifest_sha256",
            "b" * 64,
            "verification receipt manifest verification receipt verification_receipt_manifest_sha256 mismatch",
        ),
        (
            "entry_count",
            3,
            "verification receipt manifest verification receipt entry_count mismatch",
        ),
        (
            "verification_state",
            "INVALID",
            "verification receipt manifest verification receipt verification_state mismatch",
        ),
        (
            "interpretation_notice",
            "changed",
            "verification receipt manifest verification receipt interpretation_notice mismatch",
        ),
    ],
)
def test_validate_detects_body_and_digest_tampering(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: object,
    expected: str,
) -> None:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest",
        lambda manifest: [],
    )
    manifest = _manifest()
    receipt = subject.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt(
        manifest
    )
    receipt[field] = value

    findings = subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt(
        receipt,
        manifest,
    )

    assert expected in findings
    assert "verification receipt manifest verification receipt digest mismatch" in findings


def test_validate_preserves_source_findings_and_rejects_non_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest",
        lambda manifest: ["source finding"],
    )

    findings = subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt(
        [],
        _manifest(),
    )

    assert findings == [
        "source finding",
        "verification receipt manifest verification receipt must be an object",
    ]


def test_validate_rejects_extra_keys_and_digest_substitution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subject,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest",
        lambda manifest: [],
    )
    manifest = _manifest()
    receipt = subject.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt(
        manifest
    )
    receipt["unexpected"] = True
    receipt["verification_receipt_manifest_verification_receipt_sha256"] = "0" * 64

    findings = subject.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt(
        receipt,
        manifest,
    )

    assert "verification receipt manifest verification receipt keys invalid" in findings
    assert "verification receipt manifest verification receipt digest mismatch" in findings
