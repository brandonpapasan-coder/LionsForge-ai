from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.education import AssessmentAttempt, LessonProgress
from app.models.user import User
from app.schemas.education import (
    AdaptiveLearningPlanRead,
    LearningPlanItemRead,
    LearningPlanSignalRead,
)
from app.services.education import LESSONS

router = APIRouter()
MASTERY_THRESHOLD = 70
REPEATED_FAILURE_THRESHOLD = 2
ADVISORY_NOTICE = (
    "This plan is advisory. Measured performance signals are shown separately from generated guidance, "
    "and learners may review or override the recommended sequence."
)


def _difficulty(mastery_percent: int, failure_streak: int) -> str:
    if failure_streak >= REPEATED_FAILURE_THRESHOLD:
        return "foundation"
    if mastery_percent >= 75:
        return "advanced"
    if mastery_percent >= 40:
        return "intermediate"
    return "foundation"


def _failure_streaks(attempts: list[AssessmentAttempt]) -> dict[str, int]:
    streaks: dict[str, int] = defaultdict(int)
    resolved: set[str] = set()
    for attempt in attempts:
        if attempt.lesson_slug in resolved:
            continue
        if attempt.passed:
            resolved.add(attempt.lesson_slug)
            streaks.pop(attempt.lesson_slug, None)
        else:
            streaks[attempt.lesson_slug] += 1
    return dict(streaks)


def _competency_mastery(
    progress_by_slug: dict[str, LessonProgress],
) -> dict[str, int]:
    scores: dict[str, list[int]] = defaultdict(list)
    completed: dict[str, int] = defaultdict(int)
    totals: dict[str, int] = defaultdict(int)
    for lesson in LESSONS:
        competency = lesson["competency"]
        totals[competency] += 1
        progress = progress_by_slug.get(lesson["slug"])
        if progress and progress.status == "completed":
            completed[competency] += 1
        if progress and progress.score is not None:
            scores[competency].append(progress.score)

    mastery: dict[str, int] = {}
    for competency in sorted(totals):
        completion_percent = round((completed[competency] / totals[competency]) * 100)
        average_score = round(sum(scores[competency]) / len(scores[competency])) if scores[competency] else None
        mastery[competency] = (
            round((completion_percent * 0.4) + (average_score * 0.6))
            if average_score is not None
            else completion_percent
        )
    return mastery


def build_learning_plan(db: Session, user_id: int) -> AdaptiveLearningPlanRead:
    progress_rows = list(
        db.scalars(select(LessonProgress).where(LessonProgress.user_id == user_id)).all()
    )
    progress_by_slug = {row.lesson_slug: row for row in progress_rows}
    completed_slugs = {
        row.lesson_slug for row in progress_rows if row.status == "completed"
    }
    attempts = list(
        db.scalars(
            select(AssessmentAttempt)
            .where(AssessmentAttempt.user_id == user_id)
            .order_by(AssessmentAttempt.created_at.desc(), AssessmentAttempt.id.desc())
        ).all()
    )
    failure_streaks = _failure_streaks(attempts)
    mastery_by_competency = _competency_mastery(progress_by_slug)

    if not LESSONS:
        return AdaptiveLearningPlanRead(
            status="empty",
            generated_at=datetime.utcnow(),
            advisory_notice=ADVISORY_NOTICE,
            plan_items=[],
        )
    if len(completed_slugs) == len(LESSONS):
        return AdaptiveLearningPlanRead(
            status="completed",
            generated_at=datetime.utcnow(),
            advisory_notice=ADVISORY_NOTICE,
            plan_items=[],
        )

    candidates: list[tuple[int, int, dict, str, list[LearningPlanSignalRead]]] = []
    for curriculum_index, lesson in enumerate(LESSONS):
        slug = lesson["slug"]
        progress = progress_by_slug.get(slug)
        if progress and progress.status == "completed":
            continue
        missing_prerequisites = [
            item for item in lesson["prerequisites"] if item not in completed_slugs
        ]
        if missing_prerequisites:
            continue

        failure_streak = failure_streaks.get(slug, 0)
        score = progress.score if progress else None
        signals: list[LearningPlanSignalRead] = []
        if failure_streak:
            signals.append(
                LearningPlanSignalRead(
                    signal_type="unresolved_failure_streak",
                    reference=f"assessment-history:{slug}",
                    measured_value=str(failure_streak),
                    explanation=f"{failure_streak} consecutive unsuccessful assessment attempt(s) remain unresolved.",
                )
            )
        if score is not None:
            signals.append(
                LearningPlanSignalRead(
                    signal_type="latest_lesson_score",
                    reference=f"lesson-progress:{slug}",
                    measured_value=f"{score}%",
                    explanation=f"The latest recorded lesson score is {score}%.",
                )
            )
        competency_mastery = mastery_by_competency[lesson["competency"]]
        signals.append(
            LearningPlanSignalRead(
                signal_type="competency_mastery",
                reference=f"competency:{lesson['competency']}",
                measured_value=f"{competency_mastery}%",
                explanation="Competency mastery combines completed curriculum and recorded assessment performance.",
            )
        )
        if lesson["prerequisites"]:
            signals.append(
                LearningPlanSignalRead(
                    signal_type="prerequisites_complete",
                    reference=f"lesson:{slug}:prerequisites",
                    measured_value="complete",
                    explanation="All required prerequisite lessons are complete.",
                )
            )

        if failure_streak >= REPEATED_FAILURE_THRESHOLD:
            priority_score = 1000 + (failure_streak * 100) + (100 - (score or 0))
            reason = (
                f"Rebuild {lesson['competency'].replace('-', ' ')} after {failure_streak} consecutive "
                "unsuccessful attempts; use reduced difficulty until mastery is demonstrated."
            )
        elif score is not None and score < MASTERY_THRESHOLD:
            priority_score = 800 + (MASTERY_THRESHOLD - score)
            reason = (
                f"Review {lesson['title']} because the latest score of {score}% is below the "
                f"{MASTERY_THRESHOLD}% mastery threshold."
            )
        else:
            priority_score = 500 - curriculum_index
            reason = (
                f"Continue with {lesson['title']}; prerequisites are satisfied and no unresolved "
                "remediation signal has higher priority."
            )

        candidates.append(
            (priority_score, curriculum_index, lesson, reason, signals)
        )

    candidates.sort(key=lambda item: (-item[0], item[1], item[2]["slug"]))
    plan_items = [
        LearningPlanItemRead(
            sequence_position=position,
            lesson_slug=lesson["slug"],
            lesson_title=lesson["title"],
            target_competency=lesson["competency"],
            recommendation_type=(
                "remediation"
                if priority_score >= 800
                else "progression"
            ),
            priority_score=priority_score,
            recommended_difficulty=_difficulty(
                mastery_by_competency[lesson["competency"]],
                failure_streaks.get(lesson["slug"], 0),
            ),
            mastery_threshold=MASTERY_THRESHOLD,
            recommendation_reason=reason,
            supporting_signals=signals,
        )
        for position, (priority_score, _, lesson, reason, signals) in enumerate(candidates, start=1)
    ]
    return AdaptiveLearningPlanRead(
        status="active" if plan_items else "empty",
        generated_at=datetime.utcnow(),
        advisory_notice=ADVISORY_NOTICE,
        plan_items=plan_items,
    )


@router.get("", response_model=AdaptiveLearningPlanRead)
def get_learning_plan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AdaptiveLearningPlanRead:
    return build_learning_plan(db, current_user.id)
