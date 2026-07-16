from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.evidence import EvidenceRecord, EvidenceReviewEvent
from app.models.market_simulator import MarketLearningEvidenceLink, MarketLearningSession, SimulationAccount
from app.models.research_project import ResearchProject
from app.models.user import User
from app.schemas.market_learning_evidence import (
    MarketLearningEvidenceCreate,
    MarketLearningEvidenceRead,
    MarketLearningEvidenceReviewHistory,
)
from app.services.evidence_intelligence_service import build_evidence_record

router = APIRouter()

DISCLAIMER = (
    "This record is simulated educational evidence. It is not real-world empirical evidence, "
    "an investment-performance score, a market prediction, or financial advice."
)


def _next_prompt(validation_status: str) -> str:
    if validation_status == "approved":
        return "What limits prevent this simulated result from being generalized to real markets?"
    if validation_status == "rejected":
        return "Which assumption or interpretation should you revise before repeating the simulation?"
    if validation_status == "needs_review":
        return "What additional scenario or evidence would help resolve the uncertainty?"
    return "What evidence would support or challenge your interpretation of this simulated result?"


def _owned_session(db: Session, owner_id: int, session_id: int) -> MarketLearningSession:
    session = db.scalar(
        select(MarketLearningSession)
        .join(SimulationAccount, SimulationAccount.id == MarketLearningSession.account_id)
        .where(MarketLearningSession.id == session_id, SimulationAccount.owner_id == owner_id)
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Market learning session not found")
    if session.status != "completed":
        raise HTTPException(status_code=409, detail="Only completed learning sessions can become evidence")
    return session


def _owned_project(db: Session, owner_id: int, project_id: int) -> ResearchProject:
    project = db.scalar(
        select(ResearchProject).where(ResearchProject.id == project_id, ResearchProject.owner_id == owner_id)
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Research project not found")
    return project


def _link_for_session(db: Session, owner_id: int, session_id: int) -> MarketLearningEvidenceLink | None:
    return db.scalar(
        select(MarketLearningEvidenceLink).where(
            MarketLearningEvidenceLink.session_id == session_id,
            MarketLearningEvidenceLink.owner_id == owner_id,
        )
    )


def _response(link: MarketLearningEvidenceLink, session: MarketLearningSession, evidence: EvidenceRecord) -> MarketLearningEvidenceRead:
    return MarketLearningEvidenceRead(
        link_id=link.id,
        session_id=session.id,
        project_id=link.project_id,
        evidence=evidence,
        scenario_name=session.scenario_name,
        risk_tier=session.risk_tier,
        simulated_projected_return=session.projected_return,
        learner_reflection=session.learner_reflection,
        completed_at=session.completed_at,
        next_reflection_prompt=_next_prompt(evidence.validation_status),
        disclaimer=DISCLAIMER,
    )


@router.post("/learning-evidence", response_model=MarketLearningEvidenceRead, status_code=status.HTTP_201_CREATED)
def create_learning_evidence(
    payload: MarketLearningEvidenceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MarketLearningEvidenceRead:
    session = _owned_session(db, current_user.id, payload.session_id)
    _owned_project(db, current_user.id, payload.project_id)

    duplicate = _link_for_session(db, current_user.id, session.id)
    if duplicate is not None:
        raise HTTPException(
            status_code=409,
            detail={"message": "Learning session already converted to evidence", "evidence_id": duplicate.evidence_id},
        )

    evidence = build_evidence_record(
        current_user.id,
        {
            "project_id": payload.project_id,
            "entity_id": None,
            "source_url": None,
            "source_title": f"Market Simulator learning session {session.id}",
            "publisher": "LionsForge AI Market Simulator",
            "author": None,
            "published_at": session.completed_at,
            "source_type": "user",
            "claim": payload.claim.strip(),
            "excerpt": session.learner_reflection,
            "stance": payload.stance,
            "contradiction_key": payload.contradiction_key,
            "provenance": {
                "classification": "simulated_educational_evidence",
                "market_learning_session_id": session.id,
                "scenario_name": session.scenario_name,
                "risk_tier": session.risk_tier,
                "simulated_projected_return": str(session.projected_return),
                "excluded_from_empirical_evidence": True,
            },
        },
    )
    link = MarketLearningEvidenceLink(
        owner_id=current_user.id,
        session_id=session.id,
        project_id=payload.project_id,
        evidence_id=0,
    )
    db.add(evidence)
    db.flush()
    link.evidence_id = evidence.id
    db.add(link)
    db.commit()
    db.refresh(evidence)
    db.refresh(link)
    return _response(link, session, evidence)


@router.get("/learning-evidence/{session_id}", response_model=MarketLearningEvidenceReviewHistory)
def get_learning_evidence(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MarketLearningEvidenceReviewHistory:
    session = _owned_session(db, current_user.id, session_id)
    link = _link_for_session(db, current_user.id, session_id)
    if link is None:
        raise HTTPException(status_code=404, detail="Learning evidence not found")
    evidence = db.scalar(
        select(EvidenceRecord).where(EvidenceRecord.id == link.evidence_id, EvidenceRecord.owner_id == current_user.id)
    )
    if evidence is None:
        raise HTTPException(status_code=404, detail="Learning evidence not found")
    reviews = list(
        db.scalars(
            select(EvidenceReviewEvent)
            .where(
                EvidenceReviewEvent.evidence_id == evidence.id,
                EvidenceReviewEvent.owner_id == current_user.id,
            )
            .order_by(EvidenceReviewEvent.created_at, EvidenceReviewEvent.id)
        ).all()
    )
    return MarketLearningEvidenceReviewHistory(evidence=_response(link, session, evidence), reviews=reviews)
