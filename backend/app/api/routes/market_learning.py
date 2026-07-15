from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routes.market_mentor import mentor_feedback
from app.db.session import get_db
from app.models.market_simulator import MarketLearningSession, SimulationAccount
from app.models.user import User
from app.schemas.market_learning import MarketLearningSessionCreate, MarketLearningSessionRead
from app.schemas.market_simulator import PortfolioStressCreate

router = APIRouter()


def _owned_session(db: Session, owner_id: int, session_id: int) -> MarketLearningSession:
    session = db.scalar(
        select(MarketLearningSession)
        .join(SimulationAccount, SimulationAccount.id == MarketLearningSession.account_id)
        .where(
            MarketLearningSession.id == session_id,
            SimulationAccount.owner_id == owner_id,
        )
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Market learning session not found")
    return session


@router.post("/learning-sessions", response_model=MarketLearningSessionRead, status_code=status.HTTP_201_CREATED)
def create_learning_session(
    payload: MarketLearningSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MarketLearningSession:
    feedback_result = mentor_feedback(
        account_id=payload.account_id,
        payload=PortfolioStressCreate(
            scenario_name=payload.scenario_name,
            steps=payload.steps,
            seed=payload.seed,
        ),
        current_user=current_user,
        db=db,
    )
    session = MarketLearningSession(
        account_id=payload.account_id,
        scenario_name=payload.scenario_name,
        steps=payload.steps,
        seed=payload.seed,
        risk_tier=feedback_result.feedback.risk_tier,
        projected_return=feedback_result.stress.projected_return,
        learner_reflection=payload.learner_reflection.strip(),
        status="completed",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/learning-sessions", response_model=list[MarketLearningSessionRead])
def list_learning_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MarketLearningSession]:
    return list(
        db.scalars(
            select(MarketLearningSession)
            .join(SimulationAccount, SimulationAccount.id == MarketLearningSession.account_id)
            .where(SimulationAccount.owner_id == current_user.id)
            .order_by(MarketLearningSession.completed_at.desc(), MarketLearningSession.id.desc())
        ).all()
    )


@router.get("/learning-sessions/{session_id}", response_model=MarketLearningSessionRead)
def get_learning_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MarketLearningSession:
    return _owned_session(db, current_user.id, session_id)
