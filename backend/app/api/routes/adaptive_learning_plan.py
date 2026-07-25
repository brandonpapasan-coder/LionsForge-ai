from typing import Literal, cast

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routes.education import (
    REMEDIATION_SCORE_THRESHOLD,
    REPEATED_FAILURE_THRESHOLD,
    _assessment_difficulty,
    _build_hub,
    _competency_trends,
    _unresolved_failure_streaks,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.adaptive_learning_plan import (
    AdaptiveLearningPlanRead,
    LearningPlanItemRead,
    LearningPlanSignalRead,
)
from app.services.education import LESSONS

router = APIRouter()
ADVISORY_NOTICE = (
    "This plan is advisory and generated from measured education records and deterministic rules. "
    "Learners and instructors remain responsible for reviewing and adjusting the sequence."
)
PlanState = Literal["remediation", "recommended", "available", "locked"]
Difficulty = Literal["foundation", "intermediate", "advanced"]


def _difficulty_for_item(level: str, mastery_percent: int, remediation: bool) -> Difficulty:
    if remediation:
        return "foundation"
    measured_difficulty, _ = _assessment_difficulty(mastery_percent)
    if level == "foundation":
        return "foundation" if measured_difficulty == "foundation" else "intermediate"
    return cast(Difficulty, measured_difficulty)


def _priority_for_state(state: PlanState, failure_streak: int, trend_direction: str) -> int:
    if state == "remediation":
        base = 0 if failure_streak >= REPEATED_FAILURE_THRESHOLD else 10
    elif state == "recommended":
        base = 20
    elif state == "available":
        base = 30
    else:
        base = 50
    return max(0, base - 5) if trend_direction == "declining" and state != "locked" else base


def _build_learning_plan(db: Session, user_id: int) -> AdaptiveLearningPlanRead:
    hub = _build_hub(db, user_id)
    if hub.completed_lessons == hub.total_lessons:
        return AdaptiveLearningPlanRead(
            status="completed",
            advisory_notice=ADVISORY_NOTICE,
            items=[],
        )

    lessons_by_slug = {lesson.slug: lesson for lesson in hub.lessons}
    competencies = {item.competency: item for item in hub.competencies}
    trends = {item.competency: item for item in _competency_trends(db, user_id)}
    failure_streaks = _unresolved_failure_streaks(db, user_id)
    curriculum_order = {lesson["slug"]: index for index, lesson in enumerate(LESSONS)}

    ranked_items: list[tuple[int, int, str, LearningPlanItemRead]] = []
    for lesson_definition in LESSONS:
        lesson = lessons_by_slug[lesson_definition["slug"]]
        if lesson.path_state == "completed":
            continue

        competency = competencies[lesson.competency]
        trend = trends[lesson.competency]
        failure_streak = failure_streaks.get(lesson.slug, 0)
        missing_prerequisites = [
            slug for slug in lesson.prerequisites if lessons_by_slug[slug].path_state != "completed"
        ]
        state = cast(PlanState, lesson.path_state)
        priority = _priority_for_state(state, failure_streak, trend.direction)
        remediation = state == "remediation"
        difficulty = _difficulty_for_item(lesson.level, competency.mastery_percent, remediation)

        signals = [
            LearningPlanSignalRead(
                kind="lesson_progress",
                reference=f"lesson:{lesson.slug}",
                value=lesson.status,
                explanation=f"Current lesson progress is {lesson.status.replace('_', ' ')}.",
            ),
            LearningPlanSignalRead(
                kind="competency_trend",
                reference=f"competency:{lesson.competency}",
                value=trend.direction,
                explanation=trend.explanation,
            ),
        ]
        if lesson.score is not None:
            signals.append(
                LearningPlanSignalRead(
                    kind="assessment_score",
                    reference=f"lesson:{lesson.slug}:latest-score",
                    value=str(lesson.score),
                    explanation=(
                        f"The latest measured score is {lesson.score}% against the "
                        f"{REMEDIATION_SCORE_THRESHOLD}% mastery threshold."
                    ),
                )
            )
        if failure_streak:
            signals.append(
                LearningPlanSignalRead(
                    kind="failure_streak",
                    reference=f"lesson:{lesson.slug}:failure-streak",
                    value=str(failure_streak),
                    explanation=f"There are {failure_streak} unresolved unsuccessful attempts.",
                )
            )
        signals.append(
            LearningPlanSignalRead(
                kind="prerequisite_status",
                reference=f"lesson:{lesson.slug}:prerequisites",
                value="locked" if missing_prerequisites else "satisfied",
                explanation=(
                    f"Complete {', '.join(missing_prerequisites)} before this lesson unlocks."
                    if missing_prerequisites
                    else "All prerequisite lessons are complete."
                ),
            )
        )

        reason = lesson.path_reason
        if trend.direction == "declining" and state != "locked":
            reason = f"{reason} Declining competency performance increases this item's priority."
        elif trend.direction == "improving" and state not in {"locked", "remediation"}:
            reason = f"{reason} Improving performance supports continued progression."

        item = LearningPlanItemRead(
            sequence=1,
            lesson_slug=lesson.slug,
            title=lesson.title,
            target_competency=lesson.competency,
            recommended_difficulty=difficulty,
            priority=priority,
            state=state,
            reason=reason,
            mastery_threshold=REMEDIATION_SCORE_THRESHOLD,
            prerequisite_slugs=lesson.prerequisites,
            signals=signals,
        )
        ranked_items.append((priority, curriculum_order[lesson.slug], lesson.slug, item))

    ranked_items.sort(key=lambda entry: (entry[0], entry[1], entry[2]))
    items = [
        item.model_copy(update={"sequence": sequence})
        for sequence, (_, _, _, item) in enumerate(ranked_items, start=1)
    ]
    return AdaptiveLearningPlanRead(
        status="active",
        advisory_notice=ADVISORY_NOTICE,
        items=items,
    )


@router.get("/learning-plan", response_model=AdaptiveLearningPlanRead)
def get_adaptive_learning_plan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AdaptiveLearningPlanRead:
    return _build_learning_plan(db, current_user.id)
