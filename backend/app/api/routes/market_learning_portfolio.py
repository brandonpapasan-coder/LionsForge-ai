from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routes.market_learning_evidence import _next_prompt
from app.db.session import get_db
from app.models.evidence import EvidenceRecord, EvidenceReviewEvent
from app.models.market_simulator import MarketLearningEvidenceLink, MarketLearningSession, SimulationAccount
from app.models.user import User
from app.schemas.market_learning_portfolio import MarketLearningPortfolioClaim, MarketLearningPortfolioRead

router = APIRouter()

DISCLAIMER = (
    "This portfolio summarizes simulated educational learning only. It is not a record of investment performance, "
    "predictive accuracy, professional certification, real-world empirical validation, or financial advice."
)


def _maturity(completed: int, scenarios: int, submitted: int, reviewed: int) -> tuple[str, list[str]]:
    criteria = [
        f"{completed} completed learning session{'s' if completed != 1 else ''}",
        f"{scenarios} distinct scenario{'s' if scenarios != 1 else ''} explored",
        f"{submitted} learning claim{'s' if submitted != 1 else ''} submitted",
        f"{reviewed} immutable review event{'s' if reviewed != 1 else ''}",
    ]
    if completed >= 8 and scenarios >= 5 and submitted >= 5 and reviewed >= 3:
        return "evidence_informed", criteria
    if completed >= 4 and scenarios >= 3 and submitted >= 2:
        return "developing", criteria
    if completed >= 1:
        return "foundational", criteria
    return "not_started", criteria


@router.get("/learning-portfolio", response_model=MarketLearningPortfolioRead)
def get_market_learning_portfolio(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MarketLearningPortfolioRead:
    sessions = list(
        db.scalars(
            select(MarketLearningSession)
            .join(SimulationAccount, SimulationAccount.id == MarketLearningSession.account_id)
            .where(
                SimulationAccount.owner_id == current_user.id,
                MarketLearningSession.status == "completed",
            )
            .order_by(MarketLearningSession.completed_at.desc(), MarketLearningSession.id.desc())
        ).all()
    )

    links = list(
        db.scalars(
            select(MarketLearningEvidenceLink)
            .where(MarketLearningEvidenceLink.owner_id == current_user.id)
            .order_by(MarketLearningEvidenceLink.created_at.desc(), MarketLearningEvidenceLink.id.desc())
        ).all()
    )
    evidence_ids = [link.evidence_id for link in links]
    evidence_by_id = {
        evidence.id: evidence
        for evidence in (
            db.scalars(
                select(EvidenceRecord).where(
                    EvidenceRecord.owner_id == current_user.id,
                    EvidenceRecord.id.in_(evidence_ids),
                )
            ).all()
            if evidence_ids
            else []
        )
    }
    review_events = list(
        db.scalars(
            select(EvidenceReviewEvent).where(
                EvidenceReviewEvent.owner_id == current_user.id,
                EvidenceReviewEvent.evidence_id.in_(evidence_ids),
            )
        ).all()
        if evidence_ids
        else []
    )
    review_counts = Counter(event.evidence_id for event in review_events)
    session_by_id = {session.id: session for session in sessions}

    recent_claims: list[MarketLearningPortfolioClaim] = []
    for link in links:
        session = session_by_id.get(link.session_id)
        evidence = evidence_by_id.get(link.evidence_id)
        if session is None or evidence is None:
            continue
        recent_claims.append(
            MarketLearningPortfolioClaim(
                session_id=session.id,
                evidence_id=evidence.id,
                scenario_name=session.scenario_name,
                risk_tier=session.risk_tier,
                claim=evidence.claim,
                validation_status=evidence.validation_status,
                reviewer_notes=evidence.reviewer_notes,
                review_event_count=review_counts[evidence.id],
                next_reflection_prompt=_next_prompt(evidence.validation_status),
                completed_at=session.completed_at,
            )
        )
        if len(recent_claims) == 5:
            break

    scenario_counts = Counter(session.scenario_name for session in sessions)
    risk_tier_counts = Counter(session.risk_tier for session in sessions)
    validation_counts = Counter(evidence.validation_status for evidence in evidence_by_id.values())
    maturity, criteria = _maturity(
        len(sessions),
        len(scenario_counts),
        len(evidence_by_id),
        len(review_events),
    )

    return MarketLearningPortfolioRead(
        completed_sessions=len(sessions),
        unique_scenarios=len(scenario_counts),
        scenario_counts=dict(scenario_counts),
        risk_tier_counts=dict(risk_tier_counts),
        submitted_evidence=len(evidence_by_id),
        validation_status_counts=dict(validation_counts),
        immutable_review_events=len(review_events),
        learning_maturity=maturity,
        maturity_criteria=criteria,
        recent_claims=recent_claims,
        disclaimer=DISCLAIMER,
    )
