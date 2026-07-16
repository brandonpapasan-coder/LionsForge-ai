from collections import Counter, defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.evidence import ResearchReviewAction, ResearchReviewActionHistory
from app.models.research_project import ResearchProject
from app.models.user import User
from app.schemas.research_governance_dashboard import (
    GovernanceMetric,
    GovernanceThroughput,
    GovernanceTraceItem,
    ResearchGovernanceDashboard,
)

router = APIRouter()
DISCLAIMER = "Governance dashboard metrics describe review workflow and provenance risk only. They do not modify evidence or certify claim truth, accuracy, professional competence, financial outcomes, or predictive value."
STATUS_ORDER = ["open", "acknowledged", "deferred", "resolved"]
IMPACT_ORDER = ["high_attention", "review_required", "informational"]
AGE_BUCKETS = [("0_7_days", 0, 7), ("8_30_days", 8, 30), ("31_90_days", 31, 90), ("91_plus_days", 91, None)]
OVERDUE_DAYS = {"high_attention": 7, "review_required": 14, "informational": 30}


def _age_bucket(age_days: int) -> str:
    for key, minimum, maximum in AGE_BUCKETS:
        if age_days >= minimum and (maximum is None or age_days <= maximum):
            return key
    return "91_plus_days"


def _metrics(values: dict[str, list[int]], ordered_keys: list[str] | None = None) -> list[GovernanceMetric]:
    keys = ordered_keys or sorted(values)
    return [GovernanceMetric(key=key, label=key.replace("_", " ").title(), count=len(values.get(key, [])), action_ids=sorted(values.get(key, []))) for key in keys]


@router.get("/projects/{project_id}", response_model=ResearchGovernanceDashboard)
def get_research_governance_dashboard(
    project_id: int,
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchGovernanceDashboard:
    project = db.scalar(select(ResearchProject).where(ResearchProject.id == project_id, ResearchProject.owner_id == current_user.id))
    if project is None:
        raise HTTPException(status_code=404, detail="Research project not found")

    actions = list(db.scalars(select(ResearchReviewAction).where(ResearchReviewAction.owner_id == current_user.id, ResearchReviewAction.project_id == project_id).order_by(ResearchReviewAction.id)).all())
    action_ids = [item.id for item in actions]
    histories = [] if not action_ids else list(db.scalars(select(ResearchReviewActionHistory).where(ResearchReviewActionHistory.owner_id == current_user.id, ResearchReviewActionHistory.action_id.in_(action_ids)).order_by(ResearchReviewActionHistory.created_at, ResearchReviewActionHistory.id)).all())
    history_by_action: dict[int, list[ResearchReviewActionHistory]] = defaultdict(list)
    for history in histories:
        history_by_action[history.action_id].append(history)

    now = datetime.utcnow()
    status_ids: dict[str, list[int]] = defaultdict(list)
    impact_ids: dict[str, list[int]] = defaultdict(list)
    rule_ids: dict[str, list[int]] = defaultdict(list)
    age_ids: dict[str, list[int]] = defaultdict(list)
    trace_items: list[GovernanceTraceItem] = []
    overdue_count = 0
    repeatedly_reopened_count = 0

    for action in actions:
        age_days = max(0, (now - action.updated_at).days)
        bucket = _age_bucket(age_days)
        reopen_count = sum(1 for item in history_by_action[action.id] if item.previous_status == "resolved" and item.new_status == "open")
        overdue = action.status != "resolved" and age_days >= OVERDUE_DAYS[action.impact_level]
        overdue_count += int(overdue)
        repeatedly_reopened_count += int(reopen_count >= 2)
        status_ids[action.status].append(action.id)
        impact_ids[action.impact_level].append(action.id)
        rule_ids[action.governing_rule].append(action.id)
        age_ids[bucket].append(action.id)
        trace_items.append(GovernanceTraceItem(action_id=action.id, evidence_id=action.evidence_id, impact_level=action.impact_level, governing_rule=action.governing_rule, status=action.status, reason=action.reason, action_text=action.action_text, supporting_event_ids=sorted(action.supporting_event_ids), age_days=age_days, age_bucket=bucket, overdue=overdue, reopen_count=reopen_count, created_at=action.created_at, updated_at=action.updated_at))

    window_start = now - timedelta(days=days)
    recent = [item for item in histories if item.created_at >= window_start]
    resolved_action_ids = sorted({item.action_id for item in recent if item.new_status == "resolved"})
    reopened_action_ids = sorted({item.action_id for item in recent if item.previous_status == "resolved" and item.new_status == "open"})
    resolved_transitions = sum(1 for item in recent if item.new_status == "resolved")
    reopened_transitions = sum(1 for item in recent if item.previous_status == "resolved" and item.new_status == "open")

    rank = {"high_attention": 0, "review_required": 1, "informational": 2}
    trace_items.sort(key=lambda item: (not item.overdue, rank[item.impact_level], -item.reopen_count, -item.age_days, item.action_id))
    return ResearchGovernanceDashboard(
        project_id=project_id,
        generated_at=now,
        total_actions=len(actions),
        status_metrics=_metrics(status_ids, STATUS_ORDER),
        impact_metrics=_metrics(impact_ids, IMPACT_ORDER),
        rule_metrics=_metrics(rule_ids),
        aging_metrics=_metrics(age_ids, [item[0] for item in AGE_BUCKETS]),
        overdue_count=overdue_count,
        repeatedly_reopened_count=repeatedly_reopened_count,
        throughput=GovernanceThroughput(resolved_transitions=resolved_transitions, reopened_transitions=reopened_transitions, net_resolved=resolved_transitions - reopened_transitions, window_days=days, action_ids=sorted(set(resolved_action_ids + reopened_action_ids))),
        trace_items=trace_items,
        disclaimer=DISCLAIMER,
    )
