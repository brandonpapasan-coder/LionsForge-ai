from collections import Counter
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.market_simulator import MarketLearningSession, SimulationAccount
from app.models.user import User
from app.schemas.market_learning_progress import MarketLearningProgressRead

router = APIRouter()
RATE = Decimal("0.0001")
ALL_SCENARIOS = {
    "bull_market",
    "bear_market",
    "high_volatility",
    "inflation_shock",
    "rate_cut_rally",
}


@router.get("/learning-progress", response_model=MarketLearningProgressRead)
def get_learning_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MarketLearningProgressRead:
    sessions = list(
        db.scalars(
            select(MarketLearningSession)
            .join(SimulationAccount, SimulationAccount.id == MarketLearningSession.account_id)
            .where(SimulationAccount.owner_id == current_user.id)
            .order_by(MarketLearningSession.completed_at.asc(), MarketLearningSession.id.asc())
        ).all()
    )
    scenario_counts = Counter(session.scenario_name for session in sessions)
    risk_tier_counts = Counter(session.risk_tier for session in sessions)
    completed = [session for session in sessions if session.status == "completed"]
    unique_scenarios = len({session.scenario_name for session in completed})
    average_return = (
        sum((Decimal(session.projected_return) for session in completed), Decimal("0")) / len(completed)
        if completed
        else Decimal("0")
    ).quantize(RATE, rounding=ROUND_HALF_UP)

    if not completed:
        proficiency = "not_started"
        next_step = "Complete a first scenario session and record a meaningful reflection."
    elif len(completed) < 3 or unique_scenarios < 2:
        proficiency = "foundational"
        next_step = "Complete sessions across at least two contrasting market scenarios."
    elif len(completed) < 5 or unique_scenarios < 4:
        proficiency = "developing"
        next_step = "Expand scenario coverage and compare how portfolio structure changes outcomes."
    else:
        proficiency = "proficient"
        next_step = "Repeat scenarios with new seeds and explain which conclusions remain stable."

    evidence_badge_eligible = len(completed) >= 5 and ALL_SCENARIOS.issubset(scenario_counts)
    return MarketLearningProgressRead(
        total_sessions=len(sessions),
        completed_sessions=len(completed),
        unique_scenarios=unique_scenarios,
        scenario_counts=dict(sorted(scenario_counts.items())),
        risk_tier_counts=dict(sorted(risk_tier_counts.items())),
        average_projected_return=average_return,
        latest_completed_at=completed[-1].completed_at if completed else None,
        proficiency_level=proficiency,
        evidence_badge_eligible=evidence_badge_eligible,
        next_learning_step=next_step,
        disclaimer="Educational simulation progress only. This is not an investment-performance score or financial advice.",
    )
