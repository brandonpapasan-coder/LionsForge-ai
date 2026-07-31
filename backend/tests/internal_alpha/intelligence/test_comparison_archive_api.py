import copy

import pytest
from pydantic import ValidationError

from app.api.routes.internal_alpha_intelligence import (
    IntelligenceBundleInput,
    IntelligenceComparisonArchiveInput,
    IntelligenceComparisonArchiveValidationInput,
    IntelligenceComparisonInput,
    IntelligenceComparisonReceiptInput,
    IntelligenceReportInput,
    create_internal_alpha_intelligence_bundle,
    create_internal_alpha_intelligence_comparison,
    create_internal_alpha_intelligence_comparison_archive,
    create_internal_alpha_intelligence_comparison_receipt,
    create_internal_alpha_intelligence_report,
    validate_internal_alpha_intelligence_comparison_archive,
)


def _entry(candidate_sha: str, feedback_items: int = 8) -> dict[str, object]:
    payload = IntelligenceReportInput.model_validate(
        {
            "candidate_sha": candidate_sha,
            "metrics": {
                "active_testers": 5,
                "active_experiments": 2,
                "feedback_items": feedback_items,
                "completed_experiments": 1,
            },
            "readiness": {
                "security": 95.0,
                "reliability": 94.0,
                "feedback": 92.0,
                "regression": 96.0,
            },
            "repeated_categories": {},
        }
    )
    return create_internal_alpha_intelligence_report(
        payload,
        current_user=object(),  # type: ignore[arg-type]
    )


def _bundle(*entries: dict[str, object]) -> dict[str, object]:
    return create_internal_alpha_intelligence_bundle(
        IntelligenceBundleInput.model_validate({"entries": list(entries)}),
        current_user=object(),  # type: ignore[arg-type]
    )


def _fixture() -> tuple[dict[str, object], dict[str, object], dict[str, object], dict[str, object]]:
    baseline = _bundle(_entry("a" * 40), _entry("b" * 40))
    candidate = _bundle(_entry("a" * 40, 9), _entry("c" * 40))
    comparison = create_internal_alpha_intelligence_comparison(
        IntelligenceComparisonInput.model_validate(
            {"baseline": baseline, "candidate": candidate}
        ),
        current_user=object(),  # type: ignore[arg-type]
    )
    receipt = create_internal_alpha_intelligence_comparison_receipt(
        IntelligenceComparisonReceiptInput.model_validate(
            {
                "baseline": baseline,
                "candidate": candidate,
                "comparison": comparison,
            }
        ),
        current_user=object(),  # type: ignore[arg-type]
    )
    return baseline, candidate, comparison, receipt


def test_builds_and_validates_deterministic_archive() -> None:
    baseline, candidate, comparison, receipt = _fixture()
    payload = IntelligenceComparisonArchiveInput.model_validate(
        {
            "baseline": baseline,
            "candidate": candidate,
            "comparison": comparison,
            "receipt": receipt,
        }
    )
    first = create_internal_alpha_intelligence_comparison_archive(
        payload,
        current_user=object(),  # type: ignore[arg-type]
    )
    second = create_internal_alpha_intelligence_comparison_archive(
        payload,
        current_user=object(),  # type: ignore[arg-type]
    )
    assert first == second
    assert first["baseline"] == baseline
    assert first["candidate"] == candidate
    assert first["comparison"] == comparison
    assert first["receipt"] == receipt
    assert len(first["archive_sha256"]) == 64

    result = validate_internal_alpha_intelligence_comparison_archive(
        IntelligenceComparisonArchiveValidationInput.model_validate({"archive": first}),
        current_user=object(),  # type: ignore[arg-type]
    )
    assert result["valid"] is True
    assert result["findings"] == []


def test_rejects_archive_and_embedded_chain_drift() -> None:
    baseline, candidate, comparison, receipt = _fixture()
    archive = create_internal_alpha_intelligence_comparison_archive(
        IntelligenceComparisonArchiveInput.model_validate(
            {
                "baseline": baseline,
                "candidate": candidate,
                "comparison": comparison,
                "receipt": receipt,
            }
        ),
        current_user=object(),  # type: ignore[arg-type]
    )

    digest_drift = copy.deepcopy(archive)
    digest_drift["archive_sha256"] = "0" * 64
    digest_result = validate_internal_alpha_intelligence_comparison_archive(
        IntelligenceComparisonArchiveValidationInput.model_validate(
            {"archive": digest_drift}
        ),
        current_user=object(),  # type: ignore[arg-type]
    )
    assert digest_result["findings"] == ["comparison archive digest mismatch"]

    payload_drift = copy.deepcopy(archive)
    payload_drift["comparison"]["changed_candidates"] = []
    payload_result = validate_internal_alpha_intelligence_comparison_archive(
        IntelligenceComparisonArchiveValidationInput.model_validate(
            {"archive": payload_drift}
        ),
        current_user=object(),  # type: ignore[arg-type]
    )
    assert "comparison payload mismatch" in payload_result["findings"]
    assert "comparison archive digest mismatch" in payload_result["findings"]


def test_rejects_malformed_archive_and_extra_request_fields() -> None:
    malformed_result = validate_internal_alpha_intelligence_comparison_archive(
        IntelligenceComparisonArchiveValidationInput.model_validate(
            {"archive": {"schema": "invalid"}}
        ),
        current_user=object(),  # type: ignore[arg-type]
    )
    assert malformed_result["valid"] is False
    assert "comparison archive keys invalid" in malformed_result["findings"]
    assert "comparison archive payload objects invalid" in malformed_result["findings"]

    with pytest.raises(ValidationError):
        IntelligenceComparisonArchiveValidationInput.model_validate(
            {"archive": {}, "unexpected": True}
        )
