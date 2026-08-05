from copy import deepcopy

import pytest

from app.internal_alpha.intelligence import (
    comparison_archive_receipt_manifest_bundle_receipt_ledger as ledger_module,
)


def _item(seed: str, entry_count: int = 1) -> dict[str, object]:
    digest_symbols = "0123456789abcdef"
    seed_index = digest_symbols.index(seed)
    bundle_symbol = digest_symbols[(seed_index + 1) % len(digest_symbols)]
    manifest_symbol = digest_symbols[(seed_index + 2) % len(digest_symbols)]
    receipt_symbol = digest_symbols[(seed_index + 3) % len(digest_symbols)]
    return {
        "receipt": {
            "bundle_receipt_sha256": seed * 64,
            "bundle_sha256": bundle_symbol * 64,
            "manifest_sha256": manifest_symbol * 64,
            "receipt_sha256": receipt_symbol * 64,
            "entry_count": entry_count,
        },
        "bundle": {"bundle_sha256": bundle_symbol * 64},
    }


def _accept_all(receipt: dict[str, object], bundle: dict[str, object]) -> list[str]:
    del receipt, bundle
    return []


def test_build_is_deterministic_and_order_independent(monkeypatch) -> None:
    monkeypatch.setattr(
        ledger_module,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt",
        _accept_all,
    )
    first = _item("a")
    second = _item("e", entry_count=2)

    forward = ledger_module.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger(
        [first, second]
    )
    reverse = ledger_module.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger(
        [second, first]
    )

    assert forward == reverse
    assert forward["entry_count"] == 2
    assert [entry["bundle_receipt_sha256"] for entry in forward["entries"]] == [
        "a" * 64,
        "e" * 64,
    ]
    assert ledger_module.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger(
        forward
    ) == []


def test_build_rejects_duplicate_receipts(monkeypatch) -> None:
    monkeypatch.setattr(
        ledger_module,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt",
        _accept_all,
    )
    item = _item("a")

    with pytest.raises(ValueError, match="duplicate bundle receipt ledger entry"):
        ledger_module.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger(
            [item, deepcopy(item)]
        )


def test_build_rejects_invalid_receipt_bundle_pair(monkeypatch) -> None:
    def reject(receipt: dict[str, object], bundle: dict[str, object]) -> list[str]:
        del receipt, bundle
        return ["bundle receipt digest mismatch"]

    monkeypatch.setattr(
        ledger_module,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt",
        reject,
    )

    with pytest.raises(ValueError, match="bundle receipt digest mismatch"):
        ledger_module.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger(
            [_item("a")]
        )


def test_validation_fails_closed_on_order_and_digest_drift(monkeypatch) -> None:
    monkeypatch.setattr(
        ledger_module,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt",
        _accept_all,
    )
    ledger = ledger_module.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger(
        [_item("a"), _item("e")]
    )
    ledger["entries"] = list(reversed(ledger["entries"]))

    findings = ledger_module.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger(
        ledger
    )

    assert "bundle receipt ledger ordering invalid" in findings
    assert "bundle receipt ledger digest mismatch" in findings


def test_validation_rejects_duplicate_and_count_drift(monkeypatch) -> None:
    monkeypatch.setattr(
        ledger_module,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt",
        _accept_all,
    )
    ledger = ledger_module.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger(
        [_item("a"), _item("e")]
    )
    ledger["entries"][1] = deepcopy(ledger["entries"][0])
    ledger["entry_count"] = 3

    findings = ledger_module.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger(
        ledger
    )

    assert "bundle receipt ledger duplicate entry" in findings
    assert "bundle receipt ledger entry count mismatch" in findings
    assert "bundle receipt ledger digest mismatch" in findings


def test_build_enforces_bounded_item_count(monkeypatch) -> None:
    monkeypatch.setattr(
        ledger_module,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt",
        _accept_all,
    )

    with pytest.raises(ValueError, match="between 1 and 100"):
        ledger_module.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger([])
    with pytest.raises(ValueError, match="between 1 and 100"):
        ledger_module.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger(
            [_item("a") for _ in range(101)]
        )


def test_validation_rejects_coercive_schema_and_counts(monkeypatch) -> None:
    monkeypatch.setattr(
        ledger_module,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt",
        _accept_all,
    )
    ledger = ledger_module.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger(
        [_item("a")]
    )
    ledger["schema_version"] = True
    ledger["entry_count"] = True
    ledger["entries"][0]["entry_count"] = True

    findings = ledger_module.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger(
        ledger
    )

    assert "bundle receipt ledger schema version mismatch" in findings
    assert "bundle receipt ledger entry count mismatch" in findings
    assert "bundle receipt ledger entry entry_count invalid" in findings


def test_validation_rejects_malformed_entry_digests(monkeypatch) -> None:
    monkeypatch.setattr(
        ledger_module,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt",
        _accept_all,
    )
    ledger = ledger_module.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger(
        [_item("a")]
    )
    entry = ledger["entries"][0]
    entry["bundle_receipt_sha256"] = "A" * 64
    entry["bundle_sha256"] = "not-a-digest"
    entry["manifest_sha256"] = "B" * 64
    entry["receipt_sha256"] = "c" * 63

    findings = ledger_module.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger(
        ledger
    )

    assert "bundle receipt ledger entry bundle_receipt_sha256 invalid" in findings
    assert "bundle receipt ledger entry bundle_sha256 invalid" in findings
    assert "bundle receipt ledger entry manifest_sha256 invalid" in findings
    assert "bundle receipt ledger entry receipt_sha256 invalid" in findings


def test_validation_distinguishes_malformed_ledger_digest(monkeypatch) -> None:
    monkeypatch.setattr(
        ledger_module,
        "validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt",
        _accept_all,
    )
    ledger = ledger_module.build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger(
        [_item("a")]
    )
    ledger["ledger_sha256"] = "A" * 64

    findings = ledger_module.validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger(
        ledger
    )

    assert "bundle receipt ledger digest invalid" in findings
    assert "bundle receipt ledger digest mismatch" not in findings
