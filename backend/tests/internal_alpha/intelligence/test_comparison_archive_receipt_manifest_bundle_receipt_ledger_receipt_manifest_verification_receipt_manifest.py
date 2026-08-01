from copy import deepcopy

import pytest

from app.internal_alpha.intelligence import (
    comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest as module,
)


def _entry(digest: str) -> dict:
    return {
        "receipt": {
            "manifest_verification_receipt_sha256": digest,
        },
        "manifest": {"manifest_sha256": digest[::-1]},
    }


@pytest.fixture(autouse=True)
def valid_receipts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        module,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt",
        lambda receipt, manifest: [],
    )


def test_build_is_deterministic_and_canonically_orders_entries() -> None:
    high = _entry("f" * 64)
    low = _entry("0" * 64)

    first = module.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest(
        [high, low]
    )
    second = module.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest(
        [low, high]
    )

    assert first == second
    assert first["entry_count"] == 2
    assert first["entries"][0]["receipt"]["manifest_verification_receipt_sha256"] == "0" * 64
    assert first["verification_state"] == "VERIFIED"


def test_build_rejects_invalid_bounds_duplicates_and_invalid_entry() -> None:
    with pytest.raises(ValueError, match="1 to 100"):
        module.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest(
            []
        )

    duplicate = _entry("a" * 64)
    with pytest.raises(ValueError, match="duplicate receipts"):
        module.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest(
            [duplicate, deepcopy(duplicate)]
        )

    with pytest.raises(ValueError, match="entry keys invalid"):
        module.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest(
            [{"receipt": {}}]
        )


def test_build_preserves_underlying_validation_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        module,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt",
        lambda receipt, manifest: ["source manifest digest mismatch"],
    )

    with pytest.raises(ValueError, match="source manifest digest mismatch"):
        module.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest(
            [_entry("b" * 64)]
        )


def test_valid_manifest_has_no_findings() -> None:
    manifest = module.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest(
        [_entry("1" * 64), _entry("2" * 64)]
    )

    assert module.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest(
        manifest
    ) == []


def test_validator_detects_digest_order_count_and_schema_drift() -> None:
    manifest = module.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest(
        [_entry("1" * 64), _entry("2" * 64)]
    )
    drifted = deepcopy(manifest)
    drifted["schema_version"] = 2
    drifted["entry_count"] = 7
    drifted["entries"].reverse()

    findings = module.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest(
        drifted
    )

    assert "verification receipt manifest schema version mismatch" in findings
    assert "verification receipt manifest entry count mismatch" in findings
    assert "verification receipt manifest entries not canonically ordered" in findings
    assert "verification receipt manifest digest mismatch" in findings


def test_validator_rejects_non_object_extra_keys_and_duplicate_receipts() -> None:
    assert module.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest(
        []
    ) == ["verification receipt manifest must be an object"]

    duplicate = _entry("c" * 64)
    manifest = module.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest(
        [duplicate]
    )
    duplicate_manifest = deepcopy(manifest)
    duplicate_manifest["entries"].append(deepcopy(duplicate))
    duplicate_manifest["entry_count"] = 2
    duplicate_manifest["unexpected"] = True

    findings = module.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest(
        duplicate_manifest
    )

    assert "verification receipt manifest keys invalid" in findings
    assert "verification receipt manifest contains duplicate receipts" in findings
    assert "verification receipt manifest digest mismatch" in findings


def test_validator_preserves_indexed_underlying_findings(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = module.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest(
        [_entry("d" * 64)]
    )
    monkeypatch.setattr(
        module,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt",
        lambda receipt, source_manifest: ["source receipt invalid"],
    )

    findings = module.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest(
        manifest
    )

    assert any(
        finding.startswith("verification receipt manifest entry 0 invalid:")
        and "source receipt invalid" in finding
        for finding in findings
    )
