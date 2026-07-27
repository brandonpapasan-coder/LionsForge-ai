from copy import deepcopy
from datetime import datetime, timezone

import pytest

from app.services.roadmap_practicum_enrollment_receipt import (
    ADVISORY_NOTICE,
    build_action,
    build_receipt,
    canonical_json,
    validate_action,
    validate_receipt,
)

NOW = datetime(2026, 7, 27, 16, 0, tzinfo=timezone.utc)
PLAN_DIGEST = "a" * 64
PORTFOLIO_DIGEST = "b" * 64


def _action():
    return build_action(
        learner_user_id=41,
        enrollment_id=77,
        enrollment_status="not_started",
        template_slug="evidence-validation-practicum",
        template_version=2,
        research_project_id=19,
        recommendation_reason_codes=[
            "strengthens_developing_competency",
            "adds_not_yet_demonstrated_competency",
            "adds_not_yet_demonstrated_competency",
        ],
        roadmap_plan_sha256=PLAN_DIGEST,
        portfolio_sha256=PORTFOLIO_DIGEST,
        acted_at=NOW,
    )


def test_action_is_canonical_and_records_explicit_learner_intent():
    action = _action()

    assert action["action_source"] == "explicit_learner_request"
    assert action["recommendation_reason_codes"] == [
        "adds_not_yet_demonstrated_competency",
        "strengthens_developing_competency",
    ]
    assert action["advisory_notice"] == ADVISORY_NOTICE
    assert action["acted_at"] == "2026-07-27T16:00:00Z"
    assert canonical_json(action).endswith("\n")
    assert validate_action(action) == []


def test_receipt_binds_action_roadmap_and_portfolio_digests():
    action = _action()
    receipt = build_receipt(action, generated_at=NOW)

    assert receipt["roadmap_plan_sha256"] == PLAN_DIGEST
    assert receipt["portfolio_sha256"] == PORTFOLIO_DIGEST
    assert len(receipt["action_sha256"]) == 64
    assert validate_receipt(receipt, action) == []


def test_receipt_detects_action_drift_and_digest_substitution():
    action = _action()
    receipt = build_receipt(action, generated_at=NOW)
    drifted = deepcopy(action)
    drifted["research_project_id"] = 20

    assert "action digest mismatch" in validate_receipt(receipt, drifted)

    substituted = deepcopy(receipt)
    substituted["roadmap_plan_sha256"] = "c" * 64
    assert "roadmap digest binding mismatch" in validate_receipt(substituted, action)


def test_action_rejects_implicit_or_malformed_intent_and_reasons():
    action = _action()
    action["action_source"] = "automatic_recommendation"
    action["recommendation_reason_codes"] = []

    findings = validate_action(action)
    assert "action source must record explicit learner intent" in findings
    assert "recommendation reason codes are invalid" in findings


def test_action_rejects_private_content_fields():
    action = _action()
    action["project_title"] = "Private research title"

    findings = validate_action(action)
    assert "unexpected action field: project_title" in findings
    assert "prohibited private-content field at $.project_title" in findings


def test_builder_fails_closed_for_invalid_digest_or_status():
    with pytest.raises(ValueError, match="Invalid roadmap enrollment action"):
        build_action(
            learner_user_id=41,
            enrollment_id=77,
            enrollment_status="completed",
            template_slug="evidence-validation-practicum",
            template_version=2,
            research_project_id=19,
            recommendation_reason_codes=["adds_not_yet_demonstrated_competency"],
            roadmap_plan_sha256="invalid",
            portfolio_sha256=PORTFOLIO_DIGEST,
            acted_at=NOW,
        )
