from copy import deepcopy

import pytest

from app.internal_alpha.intelligence import comparison_archive_receipt_manifest as manifest_module


def _entry(digest: str) -> dict:
    return {
        "archive": {"archive_sha256": digest},
        "receipt": {"archive_sha256": digest},
    }


@pytest.fixture(autouse=True)
def valid_receipt_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        manifest_module,
        "validate_intelligence_comparison_archive_receipt",
        lambda receipt, archive: [],
    )


def test_builds_deterministic_canonically_ordered_manifest() -> None:
    later = _entry("f" * 64)
    earlier = _entry("0" * 64)

    first = manifest_module.build_intelligence_comparison_archive_receipt_manifest(
        [later, earlier]
    )
    second = manifest_module.build_intelligence_comparison_archive_receipt_manifest(
        [earlier, later]
    )

    assert first == second
    assert first["entry_count"] == 2
    assert [entry["archive"]["archive_sha256"] for entry in first["entries"]] == [
        "0" * 64,
        "f" * 64,
    ]
    assert manifest_module.validate_intelligence_comparison_archive_receipt_manifest(first) == []


def test_rejects_duplicate_archives() -> None:
    entry = _entry("a" * 64)

    with pytest.raises(ValueError, match="duplicate archives"):
        manifest_module.build_intelligence_comparison_archive_receipt_manifest(
            [entry, deepcopy(entry)]
        )


def test_rejects_unbounded_entry_counts() -> None:
    with pytest.raises(ValueError, match="1 to 100"):
        manifest_module.build_intelligence_comparison_archive_receipt_manifest([])

    with pytest.raises(ValueError, match="1 to 100"):
        manifest_module.build_intelligence_comparison_archive_receipt_manifest(
            [_entry(f"{index:064x}") for index in range(101)]
        )


def test_rejects_invalid_embedded_receipt_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        manifest_module,
        "validate_intelligence_comparison_archive_receipt",
        lambda receipt, archive: ["comparison archive receipt digest mismatch"],
    )

    with pytest.raises(ValueError, match="invalid comparison archive receipt entry"):
        manifest_module.build_intelligence_comparison_archive_receipt_manifest(
            [_entry("b" * 64)]
        )


def test_rejects_noncanonical_archive_digest() -> None:
    with pytest.raises(ValueError, match="archive digest invalid"):
        manifest_module.build_intelligence_comparison_archive_receipt_manifest(
            [_entry("A" * 64)]
        )


def test_detects_entry_drift_and_manifest_digest_drift() -> None:
    manifest = manifest_module.build_intelligence_comparison_archive_receipt_manifest(
        [_entry("1" * 64), _entry("2" * 64)]
    )
    drifted = deepcopy(manifest)
    drifted["entries"][0]["receipt"]["archive_sha256"] = "9" * 64

    findings = manifest_module.validate_intelligence_comparison_archive_receipt_manifest(
        drifted
    )

    assert "comparison archive receipt manifest digest mismatch" in findings


def test_detects_noncanonical_order_and_count_drift() -> None:
    manifest = manifest_module.build_intelligence_comparison_archive_receipt_manifest(
        [_entry("1" * 64), _entry("2" * 64)]
    )
    drifted = deepcopy(manifest)
    drifted["entries"].reverse()
    drifted["entry_count"] = 3

    findings = manifest_module.validate_intelligence_comparison_archive_receipt_manifest(
        drifted
    )

    assert "comparison archive receipt manifest entry_count mismatch" in findings
    assert "comparison archive receipt manifest entries not canonically ordered" in findings
    assert "comparison archive receipt manifest digest mismatch" in findings


def test_rejects_coercive_version_and_count_values() -> None:
    manifest = manifest_module.build_intelligence_comparison_archive_receipt_manifest(
        [_entry("1" * 64)]
    )
    manifest["schema_version"] = True
    manifest["entry_count"] = True

    findings = manifest_module.validate_intelligence_comparison_archive_receipt_manifest(
        manifest
    )

    assert "comparison archive receipt manifest schema version mismatch" in findings
    assert "comparison archive receipt manifest entry_count mismatch" in findings


def test_rejects_malformed_and_noncanonical_manifest_digests() -> None:
    manifest = manifest_module.build_intelligence_comparison_archive_receipt_manifest(
        [_entry("1" * 64)]
    )

    uppercase = deepcopy(manifest)
    uppercase["manifest_sha256"] = "A" * 64
    findings = manifest_module.validate_intelligence_comparison_archive_receipt_manifest(
        uppercase
    )
    assert "comparison archive receipt manifest digest invalid" in findings
    assert "comparison archive receipt manifest digest mismatch" in findings

    malformed = deepcopy(manifest)
    malformed["manifest_sha256"] = 7
    findings = manifest_module.validate_intelligence_comparison_archive_receipt_manifest(
        malformed
    )
    assert "comparison archive receipt manifest digest invalid" in findings
    assert "comparison archive receipt manifest digest mismatch" in findings

    substituted = deepcopy(manifest)
    substituted["manifest_sha256"] = "0" * 64
    assert manifest_module.validate_intelligence_comparison_archive_receipt_manifest(
        substituted
    ) == ["comparison archive receipt manifest digest mismatch"]


def test_fails_closed_for_malformed_manifest_and_entry() -> None:
    assert manifest_module.validate_intelligence_comparison_archive_receipt_manifest([]) == [
        "comparison archive receipt manifest must be an object"
    ]

    malformed = {
        "schema": "lionsforge.internal-alpha-intelligence-comparison-archive-receipt-manifest",
        "schema_version": 1,
        "entry_count": 1,
        "entries": [{"archive": {"archive_sha256": "a" * 64}}],
        "manifest_sha256": "0" * 64,
        "interpretation_notice": (
            "This manifest preserves bounded comparison archive receipt evidence only and does not infer "
            "causality or authorize any release transition."
        ),
    }

    findings = manifest_module.validate_intelligence_comparison_archive_receipt_manifest(
        malformed
    )

    assert any("entry 0 invalid" in finding for finding in findings)
    assert "comparison archive receipt manifest digest mismatch" in findings
