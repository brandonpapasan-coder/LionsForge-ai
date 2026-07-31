import copy

from app.api.routes.internal_alpha_intelligence import (
    IntelligenceBundleInput,
    IntelligenceComparisonInput,
    IntelligenceComparisonReceiptInput,
    IntelligenceComparisonReceiptValidationInput,
    IntelligenceReportInput,
    create_internal_alpha_intelligence_bundle,
    create_internal_alpha_intelligence_comparison,
    create_internal_alpha_intelligence_comparison_receipt,
    create_internal_alpha_intelligence_report,
    validate_internal_alpha_intelligence_comparison_receipt,
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


def _fixture() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    baseline = _bundle(_entry("a" * 40), _entry("b" * 40))
    candidate = _bundle(_entry("a" * 40, 9), _entry("c" * 40))
    comparison = create_internal_alpha_intelligence_comparison(
        IntelligenceComparisonInput.model_validate(
            {"baseline": baseline, "candidate": candidate}
        ),
        current_user=object(),  # type: ignore[arg-type]
    )
    return baseline, candidate, comparison


def test_issues_and_validates_deterministic_receipt() -> None:
    baseline, candidate, comparison = _fixture()
    create_payload = IntelligenceComparisonReceiptInput.model_validate(
        {
            "comparison": comparison,
            "baseline": baseline,
            "candidate": candidate,
        }
    )
    first = create_internal_alpha_intelligence_comparison_receipt(
        create_payload,
        current_user=object(),  # type: ignore[arg-type]
    )
    second = create_internal_alpha_intelligence_comparison_receipt(
        create_payload,
        current_user=object(),  # type: ignore[arg-type]
    )
    assert first == second
    assert first["comparison_sha256"] == comparison["comparison_sha256"]
    assert first["baseline_bundle_sha256"] == baseline["bundle_sha256"]
    assert first["candidate_bundle_sha256"] == candidate["bundle_sha256"]
    assert first["verification_state"] == "VERIFIED"
    assert len(first["receipt_sha256"]) == 64

    result = validate_internal_alpha_intelligence_comparison_receipt(
        IntelligenceComparisonReceiptValidationInput.model_validate(
            {
                "receipt": first,
                "comparison": comparison,
                "baseline": baseline,
                "candidate": candidate,
            }
        ),
        current_user=object(),  # type: ignore[arg-type]
    )
    assert result["valid"] is True
    assert result["findings"] == []


def test_rejects_receipt_and_comparison_drift() -> None:
    baseline, candidate, comparison = _fixture()
    receipt = create_internal_alpha_intelligence_comparison_receipt(
        IntelligenceComparisonReceiptInput.model_validate(
            {
                "comparison": comparison,
                "baseline": baseline,
                "candidate": candidate,
            }
        ),
        current_user=object(),  # type: ignore[arg-type]
    )
    drifted_receipt = copy.deepcopy(receipt)
    drifted_receipt["verification_state"] = "INVALID"
    receipt_result = validate_internal_alpha_intelligence_comparison_receipt(
        IntelligenceComparisonReceiptValidationInput.model_validate(
            {
                "receipt": drifted_receipt,
                "comparison": comparison,
                "baseline": baseline,
                "candidate": candidate,
            }
        ),
        current_user=object(),  # type: ignore[arg-type]
    )
    assert receipt_result["findings"] == [
        "comparison receipt verification_state mismatch",
    ]

    drifted_comparison = copy.deepcopy(comparison)
    drifted_comparison["changed_candidates"] = []
    comparison_result = validate_internal_alpha_intelligence_comparison_receipt(
        IntelligenceComparisonReceiptValidationInput.model_validate(
            {
                "receipt": receipt,
                "comparison": drifted_comparison,
                "baseline": baseline,
                "candidate": candidate,
            }
        ),
        current_user=object(),  # type: ignore[arg-type]
    )
    assert "comparison payload mismatch" in comparison_result["findings"]
