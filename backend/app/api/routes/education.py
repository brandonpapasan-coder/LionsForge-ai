from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.assessment_attempt import AssessmentAttempt
from app.models.learning_progress import LearningProgress
from app.models.user import User
from app.schemas.education import (
    AssessmentResult,
    AssessmentSubmission,
    CourseCatalogItem,
    LearningDashboard,
    LearningModule,
    LessonAssessment,
    LessonDetail,
    ModuleCompletionCreate,
    ModuleCompletionRead,
)

router = APIRouter()


def _catalog() -> list[CourseCatalogItem]:
    return [
        CourseCatalogItem(course_id="finance-foundations", title="Finance Foundations", level="beginner", description="Build fluency in markets, financial statements, risk, and valuation.", modules=[
            LearningModule(module_id="markets-101", title="How Markets Work", summary="Understand exchanges, securities, liquidity, and price discovery.", estimated_minutes=25),
            LearningModule(module_id="statements-101", title="Financial Statements", summary="Read income statements, balance sheets, and cash-flow statements.", estimated_minutes=35),
            LearningModule(module_id="risk-101", title="Risk and Return", summary="Measure volatility, drawdowns, diversification, and expected return.", estimated_minutes=30),
        ]),
        CourseCatalogItem(course_id="research-methods", title="Evidence-Based Research", level="intermediate", description="Learn to form hypotheses, test claims, validate evidence, and communicate uncertainty.", modules=[
            LearningModule(module_id="hypotheses", title="Research Hypotheses", summary="Turn broad questions into testable research claims.", estimated_minutes=30),
            LearningModule(module_id="source-quality", title="Source Quality", summary="Evaluate evidence quality, conflicts, freshness, and provenance.", estimated_minutes=35),
            LearningModule(module_id="confidence", title="Confidence and Uncertainty", summary="Calibrate conclusions and explain what could change them.", estimated_minutes=30),
        ]),
        CourseCatalogItem(course_id="advanced-strategy", title="Advanced Strategy and Portfolio Theory", level="advanced", description="Connect factor models, portfolio construction, scenario analysis, and decision discipline.", modules=[
            LearningModule(module_id="factors", title="Factor Models", summary="Interpret systematic drivers of return and risk.", estimated_minutes=40),
            LearningModule(module_id="portfolio-construction", title="Portfolio Construction", summary="Translate convictions into diversified portfolio weights.", estimated_minutes=45),
            LearningModule(module_id="scenarios", title="Scenario Analysis", summary="Stress-test assumptions across macroeconomic and company-specific regimes.", estimated_minutes=40),
        ]),
    ]


def _find_module(course_id: str, module_id: str) -> tuple[CourseCatalogItem, LearningModule] | None:
    for course in _catalog():
        if course.course_id == course_id:
            for module in course.modules:
                if module.module_id == module_id:
                    return course, module
    return None


def _completion(db: Session, user_id: int, course_id: str, module_id: str) -> LearningProgress:
    existing = db.scalar(select(LearningProgress).where(LearningProgress.user_id == user_id, LearningProgress.module_id == module_id))
    if existing is None:
        existing = LearningProgress(user_id=user_id, course_id=course_id, module_id=module_id)
        db.add(existing)
        db.commit()
        db.refresh(existing)
    return existing


def _module_metrics(db: Session, user_id: int) -> dict[str, tuple[int, int | None]]:
    rows = db.execute(
        select(AssessmentAttempt.module_id, func.count(AssessmentAttempt.id), func.max(AssessmentAttempt.score))
        .where(AssessmentAttempt.user_id == user_id)
        .group_by(AssessmentAttempt.module_id)
    ).all()
    return {module_id: (int(attempts), int(best) if best is not None else None) for module_id, attempts, best in rows}


def _recommendation(courses: list[CourseCatalogItem]) -> tuple[str, str, str]:
    incomplete = [
        (course, module)
        for course in courses
        for module in course.modules
        if not module.completed
    ]
    attempted_incomplete = [item for item in incomplete if item[1].attempt_count > 0]
    if attempted_incomplete:
        course, module = min(
            attempted_incomplete,
            key=lambda item: item[1].best_score if item[1].best_score is not None else -1,
        )
        return course.course_id, module.module_id, "Revisit this lesson because it has the lowest demonstrated mastery among unfinished modules."
    if incomplete:
        course, module = incomplete[0]
        return course.course_id, module.module_id, "Continue with the next incomplete lesson in your structured learning path."

    completed = [(course, module) for course in courses for module in course.modules]
    course, module = min(
        completed,
        key=lambda item: item[1].best_score if item[1].best_score is not None else -1,
    )
    return course.course_id, module.module_id, "Review this completed lesson to strengthen your lowest current mastery score."


@router.get("/dashboard", response_model=LearningDashboard)
def learning_dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> LearningDashboard:
    courses = _catalog()
    completed_ids = set(db.scalars(select(LearningProgress.module_id).where(LearningProgress.user_id == current_user.id)).all())
    metrics = _module_metrics(db, current_user.id)
    best_scores: list[int] = []
    for course in courses:
        for module in course.modules:
            module.completed = module.module_id in completed_ids
            module.attempt_count, module.best_score = metrics.get(module.module_id, (0, None))
            if module.best_score is not None:
                best_scores.append(module.best_score)
    recommended_course_id, recommended_module_id, recommendation_reason = _recommendation(courses)
    return LearningDashboard(
        learner_email=current_user.email,
        recommended_course_id=recommended_course_id,
        recommended_module_id=recommended_module_id,
        recommendation_reason=recommendation_reason,
        completed_modules=len(completed_ids),
        total_modules=sum(len(course.modules) for course in courses),
        mastery_average=round(sum(best_scores) / len(best_scores)) if best_scores else None,
        courses=courses,
    )


@router.get("/courses/{course_id}/modules/{module_id}", response_model=LessonDetail)
def lesson_detail(course_id: str, module_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> LessonDetail:
    match = _find_module(course_id, module_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Learning module not found")
    course, module = match
    completed = db.scalar(select(LearningProgress.id).where(LearningProgress.user_id == current_user.id, LearningProgress.module_id == module_id)) is not None
    attempts, best_score = _module_metrics(db, current_user.id).get(module_id, (0, None))
    return LessonDetail(
        course_id=course.course_id,
        module_id=module.module_id,
        course_title=course.title,
        title=module.title,
        summary=module.summary,
        estimated_minutes=module.estimated_minutes,
        objectives=[f"Explain the central concepts in {module.title}.", "Connect the lesson to evidence-based financial decisions.", "Identify one practical application and one limitation."],
        key_points=[module.summary, "Reliable decisions separate observable evidence from assumptions.", "Uncertainty should be measured, communicated, and revisited as evidence changes."],
        assessment=LessonAssessment(question=f"Which statement best summarizes the core objective of {module.title}?", options=[module.summary, "Ignore uncertainty and rely only on recent price movement.", "Replace evidence with intuition whenever conclusions are difficult."]),
        completed=completed,
        attempt_count=attempts,
        best_score=best_score,
    )


@router.post("/courses/{course_id}/modules/{module_id}/assessment", response_model=AssessmentResult)
def submit_assessment(course_id: str, module_id: str, payload: AssessmentSubmission, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> AssessmentResult:
    if _find_module(course_id, module_id) is None:
        raise HTTPException(status_code=404, detail="Learning module not found")
    passed = payload.selected_option == 0
    score = 100 if passed else 0
    db.add(AssessmentAttempt(user_id=current_user.id, course_id=course_id, module_id=module_id, selected_option=payload.selected_option, score=score, passed=passed))
    db.commit()
    completion = _completion(db, current_user.id, course_id, module_id) if passed else None
    attempts, best_score = _module_metrics(db, current_user.id)[module_id]
    return AssessmentResult(
        score=score,
        passed=passed,
        explanation="Correct. The selected answer reflects the lesson's stated learning objective." if passed else "Review the lesson summary and choose the option grounded in its stated objective.",
        completed_at=completion.completed_at if completion else None,
        attempt_count=attempts,
        best_score=best_score or score,
    )


@router.post("/completions", response_model=ModuleCompletionRead, status_code=status.HTTP_201_CREATED)
def complete_module(payload: ModuleCompletionCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ModuleCompletionRead:
    if _find_module(payload.course_id, payload.module_id) is None:
        raise HTTPException(status_code=404, detail="Learning module not found")
    existing = _completion(db, current_user.id, payload.course_id, payload.module_id)
    return ModuleCompletionRead(course_id=existing.course_id, module_id=existing.module_id, completed_at=existing.completed_at)
