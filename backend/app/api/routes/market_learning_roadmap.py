from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.evidence import EvidenceRecord
from app.models.market_simulator import MarketLearningEvidenceLink, MarketLearningSession, SimulationAccount
from app.models.user import User
from app.schemas.market_learning_roadmap import MarketLearningRoadmapRead, MarketLearningRoadmapTask

router = APIRouter()
ALL_SCENARIOS = ("bear_market", "bull_market", "high_volatility", "inflation_shock", "rate_cut_rally")
ALL_RISK_TIERS = ("low", "moderate", "high")
DISCLAIMER = (
    "This roadmap organizes simulated educational learning only. It does not provide investment recommendations, "
    "market timing, financial advice, professional certification, predictive validation, or real-world performance evidence."
)
CRITERIA = [
    "Priority 1: revisit simulated evidence that is rejected or needs review.",
    "Priority 2: submit completed learning sessions that are not yet linked to evidence.",
    "Priority 3: explore market scenarios not yet completed.",
    "Priority 4: compare risk tiers not yet represented in completed sessions.",
    "Simulated returns are excluded from task ranking.",
]


def _task_sort_key(task: MarketLearningRoadmapTask) -> tuple[int, str, str]:
    return task.priority, task.task_type, task.task_key


@router.get("/learning-roadmap", response_model=MarketLearningRoadmapRead)
def get_market_learning_roadmap(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MarketLearningRoadmapRead:
    sessions = list(
        db.scalars(
            select(MarketLearningSession)
            .join(SimulationAccount, SimulationAccount.id == MarketLearningSession.account_id)
            .where(
                SimulationAccount.owner_id == current_user.id,
                MarketLearningSession.status == "completed",
            )
            .order_by(MarketLearningSession.completed_at.asc(), MarketLearningSession.id.asc())
        ).all()
    )
    links = list(
        db.scalars(
            select(MarketLearningEvidenceLink).where(MarketLearningEvidenceLink.owner_id == current_user.id)
        ).all()
    )
    linked_session_ids = {link.session_id for link in links}
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

    tasks: list[MarketLearningRoadmapTask] = []
    for link in links:
        evidence = evidence_by_id.get(link.evidence_id)
        if evidence is None or evidence.validation_status not in {"rejected", "needs_review"}:
            continue
        tasks.append(
            MarketLearningRoadmapTask(
                task_key=f"resolve-evidence-{evidence.id}",
                task_type="resolve_evidence",
                priority=1,
                title="Revisit an unresolved learning claim",
                rationale=f"This simulated evidence is marked {evidence.validation_status.replace('_', ' ')}.",
                completion_criteria="Add a revised interpretation or complete another contrasting simulation before review.",
                reflection_prompt="Which assumption, comparison, or missing scenario would most directly address the review outcome?",
                session_id=link.session_id,
                evidence_id=evidence.id,
            )
        )

    for session in sessions:
        if session.id in linked_session_ids:
            continue
        tasks.append(
            MarketLearningRoadmapTask(
                task_key=f"submit-session-{session.id}",
                task_type="submit_evidence",
                priority=2,
                title="Convert a completed session into a learning claim",
                rationale="This completed educational simulation has not yet entered the evidence-review workflow.",
                completion_criteria="Submit one bounded claim tied to the session and an active research project.",
                reflection_prompt="What did the simulation demonstrate, and what limits prevent generalizing it to real markets?",
                scenario_name=session.scenario_name,
                risk_tier=session.risk_tier,
                session_id=session.id,
            )
        )

    completed_scenarios = {session.scenario_name for session in sessions}
    for scenario in ALL_SCENARIOS:
        if scenario in completed_scenarios:
            continue
        tasks.append(
            MarketLearningRoadmapTask(
                task_key=f"explore-scenario-{scenario}",
                task_type="explore_scenario",
                priority=3,
                title=f"Explore the {scenario.replace('_', ' ')} scenario",
                rationale="Scenario breadth supports comparison across different simulated market conditions.",
                completion_criteria="Complete the scenario and record a reflection focused on risk, assumptions, and limitations.",
                reflection_prompt="How does this scenario change the relationship between concentration, diversification, and uncertainty?",
                scenario_name=scenario,
            )
        )

    completed_risk_tiers = {session.risk_tier for session in sessions}
    for risk_tier in ALL_RISK_TIERS:
        if risk_tier in completed_risk_tiers:
            continue
        tasks.append(
            MarketLearningRoadmapTask(
                task_key=f"compare-risk-{risk_tier}",
                task_type="compare_risk_tier",
                priority=4,
                title=f"Complete a {risk_tier} risk-tier comparison",
                rationale="Risk-tier breadth helps separate scenario effects from allocation assumptions.",
                completion_criteria=f"Complete one {risk_tier} risk-tier session and compare its reflection with another tier.",
                reflection_prompt="Which conclusions changed because of the risk tier, and which remained stable?",
                risk_tier=risk_tier,
            )
        )

    tasks.sort(key=_task_sort_key)
    status = "not_started" if not sessions else ("complete" if not tasks else "active")
    return MarketLearningRoadmapRead(
        status=status,
        calculation_criteria=CRITERIA,
        tasks=tasks[:8],
        disclaimer=DISCLAIMER,
    )
