import pytest

from app.internal_alpha.intelligence.dashboard_metrics import build_metrics
from app.internal_alpha.intelligence.readiness_score import calculate_readiness_score
from app.internal_alpha.intelligence.report import build_intelligence_report


CANDIDATE = "a" * 40


def test_builds_deterministic_ready_report_without_blockers() -> None:
    report = build_intelligence_report(
        candidate_sha=CANDIDATE,
        metrics=build_metrics(
            active_testers=5,
            active_experiments=2,
            feedback_items=8,
            completed_experiments=1,
        ),
        readiness=calculate_readiness_score(
            security=95, reliability=94, feedback=92, regression=96
        ),
        repeated_categories={"USABILITY": 3, "PERFORMANCE": 2},
    )
    assert report.blocking_reasons == ()
    assert report.repeated_categories == (("USABILITY", 3), ("PERFORMANCE", 2))


def test_reports_fail_closed_blockers() -> None:
    report = build_intelligence_report(
        candidate_sha=CANDIDATE,
        metrics=build_metrics(
            active_testers=1,
            active_experiments=0,
            feedback_items=0,
            completed_experiments=0,
        ),
        readiness=calculate_readiness_score(
            security=100, reliability=100, feedback=70, regression=100
        ),
        repeated_categories={"DEFECT": 2},
    )
    assert report.blocking_reasons == (
        "NO_ACTIVE_EXPERIMENTS",
        "NO_FEEDBACK_EVIDENCE",
        "READINESS_GUARDRAIL_NOT_MET",
        "REPEATED_DEFECT_SIGNAL",
    )


def test_rejects_invalid_candidate_and_nonrepeated_counts() -> None:
    metrics = build_metrics(
        active_testers=1,
        active_experiments=1,
        feedback_items=1,
        completed_experiments=0,
    )
    readiness = calculate_readiness_score(
        security=95, reliability=95, feedback=95, regression=95
    )
    with pytest.raises(ValueError):
        build_intelligence_report(
            candidate_sha="bad", metrics=metrics, readiness=readiness, repeated_categories={}
        )
    with pytest.raises(ValueError):
        build_intelligence_report(
            candidate_sha=CANDIDATE,
            metrics=metrics,
            readiness=readiness,
            repeated_categories={"DEFECT": 1},
        )
