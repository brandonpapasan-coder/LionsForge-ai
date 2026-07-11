from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.education import LessonProgress
from app.models.user import User
from app.schemas.education import EducationHubRead, LessonProgressUpdate, LessonRead
from app.services.education import LESSON_BY_SLUG, LESSONS

router = APIRouter()


def _build_hub(db: Session, user_id: int) -> EducationHubRead:
    progress_rows = list(db.scalars(select(LessonProgress).where(LessonProgress.user_id == user_id)).all())
    progress_by_slug = {row.lesson_slug: row for row in progress_rows}

    lessons: list[LessonRead] = []
    competency_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"completed": 0, "total": 0})
    completed = 0

    for lesson in LESSONS:
        progress = progress_by_slug.get(lesson["slug"])
        status = progress.status if progress else "not_started"
        if status == "completed":
            completed += 1
            competency_counts[lesson["competency"]]["completed"] += 1
        competency_counts[lesson["competency"]]["total"] += 1
        lessons.append(
            LessonRead(
                **lesson,
                status=status,
                score=progress.score if progress else None,
                completed_at=progress.completed_at if progress else None,
            )
        )

    competencies = [
        {
            "competency": competency,
            "completed_lessons": counts["completed"],
            "total_lessons": counts["total"],
            "mastery_percent": round((counts["completed"] / counts["total"]) * 100),
        }
        for competency, counts in sorted(competency_counts.items())
    ]

    total = len(LESSONS)
    return EducationHubRead(
        completed_lessons=completed,
        total_lessons=total,
        completion_percent=round((completed / total) * 100) if total else 0,
        lessons=lessons,
        competencies=competencies,
    )


@router.get("", response_model=EducationHubRead)
def get_education_hub(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EducationHubRead:
    return _build_hub(db, current_user.id)


@router.put("/lessons/{lesson_slug}/progress", response_model=EducationHubRead)
def update_lesson_progress(
    lesson_slug: str,
    payload: LessonProgressUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EducationHubRead:
    if lesson_slug not in LESSON_BY_SLUG:
        raise HTTPException(status_code=404, detail="Lesson not found")

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
