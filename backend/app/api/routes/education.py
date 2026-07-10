from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.learning_progress import LearningProgress
from app.models.user import User
from app.schemas.education import (
    CourseCatalogItem,
    LearningDashboard,
    LearningModule,
    ModuleCompletionCreate,
    ModuleCompletionRead,
)

router = APIRouter()


def _catalog() -> list[CourseCatalogItem]:
    return [
        CourseCatalogItem(
            course_id="finance-foundations",
            title="Finance Foundations",
            level="beginner",
            description="Build fluency in markets, financial statements, risk, and valuation.",
            modules=[
                LearningModule(module_id="markets-101", title="How Markets Work", summary="Understand exchanges, securities, liquidity, and price discovery.", estimated_minutes=25),
                LearningModule(module_id="statements-101", title="Financial Statements", summary="Read income statements, balance sheets, and cash-flow statements.", estimated_minutes=35),
                LearningModule(module_id="risk-101", title="Risk and Return", summary="Measure volatility, drawdowns, diversification, and expected return.", estimated_minutes=30),
            ],
        ),
        CourseCatalogItem(
            course_id="research-methods",
            title="Evidence-Based Research",
            level="intermediate",
            description="Learn to form hypotheses, test claims, validate evidence, and communicate uncertainty.",
            modules=[
                LearningModule(module_id="hypotheses", title="Research Hypotheses", summary="Turn broad questions into testable research claims.", estimated_minutes=30),
                LearningModule(module_id="source-quality", title="Source Quality", summary="Evaluate evidence quality, conflicts, freshness, and provenance.", estimated_minutes=35),
                LearningModule(module_id="confidence", title="Confidence and Uncertainty", summary="Calibrate conclusions and explain what could change them.", estimated_minutes=30),
            ],
        ),
        CourseCatalogItem(
            course_id="advanced-strategy",
            title="Advanced Strategy and Portfolio Theory",
            level="advanced",
            description="Connect factor models, portfolio construction, scenario analysis, and decision discipline.",
            modules=[
                LearningModule(module_id="factors", title="Factor Models", summary="Interpret systematic drivers of return and risk.", estimated_minutes=40),
                LearningModule(module_id="portfolio-construction", title="Portfolio Construction", summary="Translate convictions into diversified portfolio weights.", estimated_minutes=45),
                LearningModule(module_id="scenarios", title="Scenario Analysis", summary="Stress-test assumptions across macroeconomic and company-specific regimes.", estimated_minutes=40),
            ],
        ),
    ]


def _valid_module(course_id: str, module_id: str) -> bool:
    return any(
        course.course_id == course_id and any(module.module_id == module_id for module in course.modules)
        for course in _catalog()
    )


@router.get("/dashboard", response_model=LearningDashboard)
def learning_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LearningDashboard:
    courses = _catalog()
    completed_ids = set(
        db.scalars(select(LearningProgress.module_id).where(LearningProgress.user_id == current_user.id)).all()
    )
    for course in courses:
        for module in course.modules:
            module.completed = module.module_id in completed_ids
    return LearningDashboard(
        learner_email=current_user.email,
        recommended_course_id="finance-foundations",
        completed_modules=len(completed_ids),
        total_modules=sum(len(course.modules) for course in courses),
        courses=courses,
    )


@router.post("/completions", response_model=ModuleCompletionRead, status_code=status.HTTP_201_CREATED)
def complete_module(
    payload: ModuleCompletionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ModuleCompletionRead:
    if not _valid_module(payload.course_id, payload.module_id):
        raise HTTPException(status_code=404, detail="Learning module not found")

    existing = db.scalar(
        select(LearningProgress).where(
            LearningProgress.user_id == current_user.id,
            LearningProgress.module_id == payload.module_id,
        )
    )
    if existing is None:
        existing = LearningProgress(
            user_id=current_user.id,
            course_id=payload.course_id,
            module_id=payload.module_id,
        )
        db.add(existing)
        db.commit()
        db.refresh(existing)

    return ModuleCompletionRead(
        course_id=existing.course_id,
        module_id=existing.module_id,
        completed_at=existing.completed_at,
    )
