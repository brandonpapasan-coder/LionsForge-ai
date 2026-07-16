from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.evidence import EvidenceRecord, EvidenceReviewEvent
from app.models.market_simulator import MarketLearningEvidenceLink, MarketLearningSession, SimulationAccount
from app.models.user import User
from app.schemas.market_learning_mastery import MarketLearningMasteryDimension, MarketLearningMasteryRead

router = APIRouter()
DISCLAIMER = (
    "This assessment summarizes simulated educational practice only. It is not investment-performance evidence, "
    "predictive validation, accreditation, professional certification, employability validation, or financial advice."
)
CRITERIA = [
    "Each rubric dimension uses deterministic count and quality thresholds.",
    "Only owner-scoped completed sessions, linked learning evidence, and immutable review events are counted.",
    "Reflection quality uses the presence and specificity of learner-written reflections, not market outcomes.",
    "Simulated returns, gains, losses, and portfolio outcomes are excluded from every assessment rule.",
]


def _dimension(
    key: str,
    title: str,
    count: int,
    target: int,
    criteria: str,
    next_action: str,
    developing_at: int = 1,
) -> MarketLearningMasteryDimension:
    status = "met" if count >= target else ("developing" if count >= developing_at else "not_started")
    unmet = [] if status == "met" else [f"Current evidence: {count}; target: {target}."]
    return MarketLearningMasteryDimension(
        key=key,
        title=title,
        status=status,
        evidence_count=count,
        target_count=target,
        criteria=criteria,
        unmet_criteria=unmet,
        next_action=next_action,
    )


@router.get("/learning-mastery", response_model=MarketLearningMasteryRead)
def get_market_learning_mastery(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MarketLearningMasteryRead:
    sessions = list(
        db.scalars(
            select(MarketLearningSession)
            .join(SimulationAccount, SimulationAccount.id == MarketLearningSession.account_id)
            .where(
                SimulationAccount.owner_id == current_user.id,
                MarketLearningSession.status == "completed",
            )
            .order_by(MarketLearningSession.completed_at, MarketLearningSession.id)
        ).all()
    )
    links = list(
        db.scalars(
            select(MarketLearningEvidenceLink).where(MarketLearningEvidenceLink.owner_id == current_user.id)
        ).all()
    )
    evidence_ids = [link.evidence_id for link in links]
    evidence = list(
        db.scalars(
            select(EvidenceRecord).where(
                EvidenceRecord.owner_id == current_user.id,
                EvidenceRecord.id.in_(evidence_ids),
            )
        ).all()
        if evidence_ids
        else []
    )
    reviews = list(
        db.scalars(
            select(EvidenceReviewEvent).where(
                EvidenceReviewEvent.owner_id == current_user.id,
                EvidenceReviewEvent.evidence_id.in_(evidence_ids),
            )
        ).all()
        if evidence_ids
        else []
    )

    scenario_count = len({session.scenario_name for session in sessions})
    risk_tier_count = len({session.risk_tier for session in sessions})
    reviewed_evidence_count = len({event.evidence_id for event in reviews})
    contradiction_groups = Counter(
        item.contradiction_key for item in evidence if item.contradiction_key and item.stance in {"supports", "contradicts"}
    )
    contradiction_handling_count = sum(1 for count in contradiction_groups.values() if count >= 2)
    substantive_reflections = sum(1 for session in sessions if len(session.learner_reflection.strip()) >= 80)

    dimensions = [
        _dimension(
            "scenario_breadth",
            "Scenario breadth",
            scenario_count,
            4,
            "Complete at least four distinct simulated scenarios.",
            "Complete a scenario not yet represented and compare its assumptions with a prior session.",
        ),
        _dimension(
            "risk_tier_comparison",
            "Risk-tier comparison",
            risk_tier_count,
            3,
            "Represent low, moderate, and high educational risk tiers.",
            "Complete a missing risk tier and write a cross-tier comparison.",
        ),
        _dimension(
            "evidence_discipline",
            "Evidence submission discipline",
            len(evidence),
            4,
            "Submit at least four bounded claims linked to completed sessions.",
            "Convert another completed session into a claim with explicit limitations.",
        ),
        _dimension(
            "review_follow_through",
            "Review follow-through",
            reviewed_evidence_count,
            3,
            "Complete immutable review activity for at least three learning claims.",
            "Review an unreviewed claim or revise one marked needs review or rejected.",
        ),
        _dimension(
            "contradiction_handling",
            "Contradiction handling",
            contradiction_handling_count,
            1,
            "Create at least one contradiction group containing multiple perspectives.",
            "Submit a contrasting claim under the same contradiction key and reconcile the disagreement.",
        ),
        _dimension(
            "reflection_quality",
            "Reflection quality",
            substantive_reflections,
            5,
            "Record at least five substantive reflections of 80 or more characters.",
            "Expand a reflection to explain assumptions, limitations, and what would change the conclusion.",
        ),
    ]
    met = sum(1 for dimension in dimensions if dimension.status == "met")
    if not sessions:
        readiness = "not_started"
    elif met >= 5:
        readiness = "evidence_informed"
    elif met >= 3:
        readiness = "developing"
    else:
        readiness = "foundational"

    return MarketLearningMasteryRead(
        overall_readiness=readiness,
        dimensions_met=met,
        dimensions_total=len(dimensions),
        calculation_criteria=CRITERIA,
        dimensions=dimensions,
        disclaimer=DISCLAIMER,
    )
