from copy import deepcopy
from datetime import datetime, timezone

from app.services.learner_competency_gap_plan import (
    ADVISORY_NOTICE,
    build_plan,
    build_receipt,
    validate_plan,
    validate_receipt,
)

NOW = datetime(2026, 7, 27, 4, 10, tzinfo=timezone.utc)
PORTFOLIO_DIGEST = "a" * 64


def _plan():
    return build_plan(
        learner_user_id=7,
        generated_at=NOW,
        portfolio_sha256=PORTFOLIO_DIGEST,
        competency_rows=[
            {"competency_key": "source_validation", "competency_label": "Source Validation", "completed_practicum_count": 2},
            {"competency_key": "research_design", "competency_label": "Research Design", "completed_practicum_count": 1},
        ],
        template_rows=[
            {
                "template_slug": "advanced-validation",
                "template_version": 2,
                "objective_keys": ["validate-2", "validate-1"],
                "competency_keys": ["source_validation"],
                "estimated_minutes": 90,
                "prerequisite_lesson_slugs": ["evidence-basics"],
            },
            {
                "template_slug": "bias-audit",
                "template_version": 1,
                "objective_keys": ["bias-detection"],
                "competency_keys": ["bias_detection"],
                "estimated_minutes": 45,
                "prerequisite_lesson_slugs": [],
            },
            {
                "template_slug": "research-design-lab",
                "template_version": 1,
                "objective_keys": ["design-study"],
                "competency_keys": ["research_design"],
                "estimated_minutes": 60,
                "prerequisite_lesson_slugs": ["research-foundations"],
            },
        ],
        completed_template_versions={"advanced-validation", 2} if False else {("advanced-validation", 2)},
    )


def test_build_plan_classifies_and_recommends_deterministically():
    plan = _plan()
    assert plan["advisory_notice"] == ADVISORY_NOTICE
    assert [item["status"] for item in plan["competencies"]] == ["developing", "demonstrated"]
    assert [item["template_slug"] for item in plan["recommendations"]] == ["bias-audit", "research-design-lab"]
    assert plan["recommendations"][0]["reason_codes"] == ["adds_not_yet_demonstrated_competency"]
    assert plan["recommendations"][1]["reason_codes"] == ["strengthens_developing_competency"]
    assert validate_plan(plan) == []


def test_receipt_binds_plan_and_portfolio_digest():
    plan = _plan()
    receipt = build_receipt(plan, generated_at=NOW)
    assert receipt["portfolio_sha256"] == PORTFOLIO_DIGEST
    assert validate_receipt(receipt, plan) == []

    drifted = deepcopy(plan)
    drifted["recommendations"][0]["estimated_minutes"] = 46
    assert "plan digest mismatch" in validate_receipt(receipt, drifted)


def test_validation_rejects_private_fields_and_threshold_drift():
    plan = _plan()
    plan["private_content"] = "hidden"
    assert any("prohibited private-content field" in item for item in validate_plan(plan))

    plan = _plan()
    plan["competencies"][0]["status"] = "demonstrated"
    assert "competency status does not match deterministic threshold" in validate_plan(plan)


def test_completed_and_fully_demonstrated_templates_are_excluded():
    plan = _plan()
    slugs = {item["template_slug"] for item in plan["recommendations"]}
    assert "advanced-validation" not in slugs
