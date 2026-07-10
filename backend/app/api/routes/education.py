from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.education import CourseCatalogItem, LearningDashboard, LearningModule

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


@router.get("/dashboard", response_model=LearningDashboard)
def learning_dashboard(current_user: User = Depends(get_current_user)) -> LearningDashboard:
    courses = _catalog()
    return LearningDashboard(
        learner_email=current_user.email,
        recommended_course_id="finance-foundations",
        completed_modules=0,
        total_modules=sum(len(course.modules) for course in courses),
        courses=courses,
    )
