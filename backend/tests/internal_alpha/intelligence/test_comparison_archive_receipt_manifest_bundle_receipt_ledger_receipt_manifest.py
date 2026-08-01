import copy

import pytest

from app.internal_alpha.intelligence import (
    comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest as manifest_module,
)


def _pair(digest: str) -> dict[str, object]:
    return {
        "receipt": {
            "ledger_receipt_sha256": digest,
            "ledger_sha256": ("a" if digest.startswith("1") else "b") * 64,
            "entry_count": 1,
        },
        "ledger": {
            "ledger_sha256": ("a" if digest.startswith("1") else "b") * 64,
            "entry_count": 1,
        },
    }


def _accept_valid_pair(receipt: dict[str, object], ledger: dict[str, object]) -> list[str]:
    if receipt.get("ledger_sha256") != ledger.get("ledger_sha256"):
        return ["ledger receipt binding mismatch"]
    return []


def test_manifest_rejects_bounds(monkeypatch) -> None:
    monkeypatch.setattr(
        manifest_module,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt",
        _accept_valid_pair,
    )

    with pytest.raises(ValueError, match="1 to 100"):
        manifest_module.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest(
            []
        )
    with pytest.raises(ValueError, match="1 to 100"):
        manifest_module.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest(
            [_pair(f"{index:064x}") for index in range(101)]
        )


def test_manifest_rejects_invalid_and_duplicate_entries(monkeypatch) -> None:
    monkeypatch.setattr(
        manifest_module,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt",
        _accept_valid_pair,
    )
    invalid = _pair("1" * 64)
    invalid["ledger"] = {"ledger_sha256": "c" * 64, "entry_count": 1}

    with pytest.raises(ValueError, match="invalid ledger receipt manifest entry"):
        manifest_module.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest(
            [invalid]
        )

    duplicate = _pair("1" * 64)
    with pytest.raises(ValueError, match="duplicate receipts"):
        manifest_module.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest(
            [duplicate, copy.deepcopy(duplicate)]
        )


def test_manifest_is_order_independent_and_validates(monkeypatch) -> None:
    monkeypatch.setattr(
        manifest_module,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt",
        _accept_valid_pair,
    )
    first = _pair("1" * 64)
    second = _pair("2" * 64)

    left = manifest_module.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest(
        [second, first]
    )
    right = manifest_module.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest(
        [first, second]
    )

    assert left == right
    assert [entry["receipt"]["ledger_receipt_sha256"] for entry in left["entries"]] == [
        "1" * 64,
        "2" * 64,
    ]
    assert (
        manifest_module.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest(
            left
        )
        == []
    )


def test_validator_rejects_order_duplicates_and_digest_drift(monkeypatch) -> None:
    monkeypatch.setattr(
        manifest_module,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt",
        _accept_valid_pair,
    )
    first = _pair("1" * 64)
    second = _pair("2" * 64)
    manifest = manifest_module.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest(
        [first, second]
    )

    reordered = copy.deepcopy(manifest)
    reordered["entries"].reverse()
    findings = manifest_module.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest(
        reordered
    )
    assert "ledger receipt manifest entries not canonically ordered" in findings
    assert "ledger receipt manifest digest mismatch" in findings

    duplicated = copy.deepcopy(manifest)
    duplicated["entries"][1] = copy.deepcopy(duplicated["entries"][0])
    findings = manifest_module.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest(
        duplicated
    )
    assert "ledger receipt manifest contains duplicate receipts" in findings
    assert "ledger receipt manifest digest mismatch" in findings

    drifted = copy.deepcopy(manifest)
    drifted["manifest_sha256"] = "f" * 64
    assert "ledger receipt manifest digest mismatch" in (
        manifest_module.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest(
            drifted
        )
    )


def test_validator_fails_closed_on_malformed_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        manifest_module,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt",
        _accept_valid_pair,
    )

    assert manifest_module.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest(
        []  # type: ignore[arg-type]
    ) == ["ledger receipt manifest must be an object"]

    malformed = {
        "schema": "wrong",
        "schema_version": 2,
        "entry_count": 0,
        "entries": [],
        "verification_state": "UNVERIFIED",
        "interpretation_notice": "wrong",
        "manifest_sha256": "0" * 64,
    }
    findings = manifest_module.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest(
        malformed
    )
    assert "ledger receipt manifest schema mismatch" in findings
    assert "ledger receipt manifest schema version mismatch" in findings
    assert "ledger receipt manifest verification state mismatch" in findings
    assert "ledger receipt manifest interpretation notice mismatch" in findings
    assert "ledger receipt manifest entries invalid" in findings
