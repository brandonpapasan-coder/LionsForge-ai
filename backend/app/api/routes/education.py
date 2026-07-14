from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.education import LessonProgress
from app.models.user import User
from app.schemas.education import (
    AdaptiveAssessmentRead,
    AssessmentQuestionRead,
    AssessmentResultRead,
    AssessmentSubmission,
    EducationHubRead,
    LessonProgressUpdate,
    LessonRead,
)
from app.services.assessments import ASSESSMENT_BANK
from app.services.education import LESSON_BY_SLUG, LESSONS

router = APIRouter()
REMEDIATION_SCORE_THRESHOLD = 70
ASSESSMENT_PASS_SCORE = 70


@dataclass
class CompetencyAccumulator:
    completed: int = 0
    total: int = 0
    scores: list[int] = field(default_factory=list)


def _proficiency_band(mastery_percent: int) -> str:
    if mastery_percent >= 90:
        return "expert"
    if mastery_percent >= 75:
        return "advanced"
    if mastery_percent >= 60:
        return "proficient"
    if mastery_percent >= 40:
        return "developing"
    return "foundation"


def _assessment_difficulty(mastery_percent: int) -> tuple[str, str]:
    if mastery_percent >= 75:
        return "advanced", f"Advanced difficulty selected because mastery is {mastery_percent}%."
    if mastery_percent >= 40:
        return "intermediate", f"Intermediate difficulty selected because mastery is {mastery_percent}%."
    return "foundation", f"Foundation difficulty selected because mastery is {mastery_percent}%."


def _humanize(value: str) -> str:
    return value.replace("-", " ")


def _prerequisite_titles(prerequisites: list[str]) -> str:
    return ", ".join(LESSON_BY_SLUG[slug]["title"] for slug in prerequisites)


def _build_hub(db: Session, user_id: int) -> EducationHubRead:
    progress_rows = list(db.scalars(select(LessonProgress).where(LessonProgress.user_id == user_id)).all())
    progress_by_slug = {row.lesson_slug: row for row in progress_rows}
    completed_slugs = {row.lesson_slug for row in progress_rows if row.status == "completed"}

    competency_counts: dict[str, CompetencyAccumulator] = defaultdict(CompetencyAccumulator)
    completed = 0
    scores: list[int] = []

    for lesson in LESSONS:
        progress = progress_by_slug.get(lesson["slug"])
        status = progress.status if progress else "not_started"
        score = progress.score if progress else None
        competency = competency_counts[lesson["competency"]]
        if status == "completed":
            completed += 1
            competency.completed += 1
        if score is not None:
            scores.append(score)
            competency.scores.append(score)
        competency.total += 1

    competencies = []
    competency_metrics: dict[str, tuple[int | None, int]] = {}
    for competency_name, counts in sorted(competency_counts.items()):
        completion_component = round((counts.completed / counts.total) * 100)
        average_score = round(sum(counts.scores) / len(counts.scores)) if counts.scores else None
        mastery_percent = (
            round((completion_component * 0.4) + (average_score * 0.6))
            if average_score is not None
            else completion_component
        )
        competency_metrics[competency_name] = (average_score, mastery_percent)
        competencies.append(
            {
                "competency": competency_name,
                "completed_lessons": counts.completed,
                "total_lessons": counts.total,
                "assessed_lessons": len(counts.scores),
                "average_score": average_score,
                "mastery_percent": mastery_percent,
                "proficiency_band": _proficiency_band(mastery_percent),
            }
        )

    lesson_states: dict[str, tuple[str, str]] = {}
    for lesson in LESSONS:
        slug = lesson["slug"]
        progress = progress_by_slug.get(slug)
        prerequisites = lesson["prerequisites"]
        missing_prerequisites = [item for item in prerequisites if item not in completed_slugs]
        if progress and progress.status == "completed":
            lesson_states[slug] = ("completed", "Lesson completed and prerequisite credit earned.")
        elif missing_prerequisites:
            lesson_states[slug] = (
                "locked",
                f"Complete {_prerequisite_titles(missing_prerequisites)} before this lesson becomes available.",
            )
        elif progress and progress.score is not None and progress.score < REMEDIATION_SCORE_THRESHOLD:
            lesson_states[slug] = (
                "remediation",
                f"Review this lesson because the latest score of {progress.score}% is below the "
                f"{REMEDIATION_SCORE_THRESHOLD}% mastery threshold.",
            )
        else:
            lesson_states[slug] = ("available", "All prerequisites are complete; this lesson is available.")

    recommended_lesson_slug: str | None = None
    recommendation_reason = "All current lessons are complete."

    remediation_candidates = sorted(
        (
            (progress_by_slug[lesson["slug"]].score, index, lesson)
            for index, lesson in enumerate(LESSONS)
            if lesson_states[lesson["slug"]][0] == "remediation"
        ),
        key=lambda item: (item[0], item[1]),
    )
    if remediation_candidates:
        score, _, lesson = remediation_candidates[0]
        recommended_lesson_slug = lesson["slug"]
        recommendation_reason = (
            f"Strengthen {_humanize(lesson['competency'])}: the latest {score}% assessment score is below the "
            f"{REMEDIATION_SCORE_THRESHOLD}% mastery threshold."
        )
    else:
        available_lesson = next(
            (lesson for lesson in LESSONS if lesson_states[lesson["slug"]][0] == "available"),
            None,
        )
        if available_lesson is not None:
            recommended_lesson_slug = available_lesson["slug"]
            prerequisites = available_lesson["prerequisites"]
            recommendation_reason = (
                f"Continue with {available_lesson['title']}; its prerequisite lessons are complete."
                if prerequisites
                else "Continue the curriculum with the next available foundation lesson."
            )

    lessons: list[LessonRead] = []
    for lesson in LESSONS:
        progress = progress_by_slug.get(lesson["slug"])
        status = progress.status if progress else "not_started"
        path_state, path_reason = lesson_states[lesson["slug"]]
        if lesson["slug"] == recommended_lesson_slug:
            path_state = "remediation" if path_state == "remediation" else "recommended"
            path_reason = recommendation_reason
        lessons.append(
            LessonRead(
                **lesson,
                status=status,
                score=progress.score if progress else None,
                completed_at=progress.completed_at if progress else None,
                path_state=path_state,
                path_reason=path_reason,
            )
        )

    total = len(LESSONS)
    completion_percent = round((completed / total) * 100) if total else 0
    average_score = round(sum(scores) / len(scores)) if scores else None
    mastery_percent = (
        round((completion_percent * 0.4) + (average_score * 0.6))
        if average_score is not None
        else completion_percent
    )
    return EducationHubRead(
        completed_lessons=completed,
        total_lessons=total,
        assessed_lessons=len(scores),
        completion_percent=completion_percent,
        average_score=average_score,
        mastery_percent=mastery_percent,
        proficiency_band=_proficiency_band(mastery_percent),
        recommended_lesson_slug=recommended_lesson_slug,
        recommendation_reason=recommendation_reason,
        lessons=lessons,
        competencies=competencies,
    )


def _assessment_for_user(db: Session, user_id: int) -> AdaptiveAssessmentRead:
    hub = _build_hub(db, user_id)
    if hub.recommended_lesson_slug is None:
        raise HTTPException(status_code=409, detail="All current lessons are complete")

    lesson = LESSON_BY_SLUG[hub.recommended_lesson_slug]
    competency = next(item for item in hub.competencies if item.competency == lesson["competency"])
    difficulty, reason = _assessment_difficulty(competency.mastery_percent)
    question = ASSESSMENT_BANK[lesson["slug"]][difficulty]
    return AdaptiveAssessmentRead(
        lesson_slug=lesson["slug"],
        competency=lesson["competency"],
        difficulty=difficulty,
        difficulty_reason=reason,
        question=AssessmentQuestionRead(
            id=question["id"],
            prompt=question["prompt"],
            options=question["options"],
            objective=question["objective"],
        ),
    )


@router.get("", response_model=EducationHubRead)
def get_education_hub(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EducationHubRead:
    return _build_hub(db, current_user.id)


@router.get("/assessment", response_model=AdaptiveAssessmentRead)
def get_adaptive_assessment(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AdaptiveAssessmentRead:
    return _assessment_for_user(db, current_user.id)


@router.post("/assessment", response_model=AssessmentResultRead)
def submit_adaptive_assessment(
    payload: AssessmentSubmission,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AssessmentResultRead:
    assessment = _assessment_for_user(db, current_user.id)
    question = ASSESSMENT_BANK[assessment.lesson_slug][assessment.difficulty]
    if payload.question_id != question["id"]:
        raise HTTPException(status_code=409, detail="Assessment question is no longer current")
    if payload.selected_option >= len(question["options"]):
        raise HTTPException(status_code=422, detail="Selected option is out of range")

    score = 100 if payload.selected_option == question["correct_option"] else 0
    passed = score >= ASSESSMENT_PASS_SCORE
    progress = db.scalar(
        select(LessonProgress).where(
            LessonProgress.user_id == current_user.id,
            LessonProgress.lesson_slug == assessment.lesson_slug,
        )
    )
    if progress is None:
        progress = LessonProgress(user_id=current_user.id, lesson_slug=assessment.lesson_slug)
        db.add(progress)
    progress.status = "completed" if passed else "in_progress"
    progress.score = score
    progress.completed_at = datetime.utcnow() if passed else None
    db.commit()

    feedback = (
        f"Mastery demonstrated for {_humanize(assessment.competency)}."
        if passed
        else f"Review {_humanize(assessment.competency)} and retry the recommended lesson."
    )
    return AssessmentResultRead(
        lesson_slug=assessment.lesson_slug,
        competency=assessment.competency,
        difficulty=assessment.difficulty,
        score=score,
        passed=passed,
        feedback=feedback,
        learning_objective=question["objective"],
        education_hub=_build_hub(db, current_user.id),
    )


@router.put("/lessons/{lesson_slug}/progress", response_model=EducationHubRead)
def update_lesson_progress(
    lesson_slug: str,
    payload: LessonProgressUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EducationHubRead:
    if lesson_slug not in LESSON_BY_SLUG:
        raise HTTPException(status_code=404, detail="Lesson not found")

    current_hub = _build_hub(db, current_user.id)
    lesson_state = next(item.path_state for item in current_hub.lessons if item.slug == lesson_slug)
    if lesson_state == "locked":
        raise HTTPException(status_code=409, detail="Lesson prerequisites are not complete")

    progress = db.scalar(
        select(LessonProgress).where(
            LessonProgress.user_id == current_user.id,
            LessonProgress.lesson_slug == lesson_slug,
        )
    )
    if progress is None:
        progress = LessonProgress(user_id=current_user.id, lesson_slug=lesson_slug)
        db.add(progress)

    progress.status = payload.status
    progress.score = payload.score
    progress.completed_at = datetime.utcnow() if payload.status == "completed" else None
    db.commit()

    return _build_hub(db, current_user.id)
