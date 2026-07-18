from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.evidence import ResearchReviewAction
from app.models.user import User
from app.schemas.research_follow_up_tracker import (
    RemediationEscalationInventory,
    RemediationEscalationItem,
    RemediationEscalationState,
)

router = APIRouter()
_TERMINAL = {"resolved", "dismissed"}
_THRESHOLDS = {
    "urgent": {"aging": 1, "overdue": 2, "critical": 4},
    "high": {"aging": 2, "overdue": 5, "critical": 10},
    "normal": {"aging": 7, "overdue": 14, "critical": 30},
    "low": {"aging": 14, "overdue": 30, "critical": 60},
}
_STATE_RANK = {"critical": 0, "overdue": 1, "aging": 2, "fresh": 3}
DISCLAIMER = (
    "Escalation states prioritize owner review of research follow-ups only. "
    "They do not certify evidence, resolve actions automatically, or imply claim truth."
)


def _state_for(action: ResearchReviewAction, now: datetime) -> tuple[str, int, int, datetime | None]:
    age_days = max(0, (now - action.created_at).days)
    idle_days = max(0, (now - action.updated_at).days)
    thresholds = _THRESHOLDS.get(action.priority, _THRESHOLDS["normal"])
    days_overdue = max(0, (now - action.due_at).days) if action.due_at and action.due_at < now else 0

    if action.due_at is not None and action.due_at < now:
        state = "critical" if days_overdue >= thresholds["overdue"] else "overdue"
        next_escalation_at = None if state == "critical" else action.due_at + timedelta(days=thresholds["overdue"])
        return state, age_days, idle_days, next_escalation_at

    basis_days = max(age_days, idle_days)
    if basis_days >= thresholds["critical"]:
        return "critical", age_days, idle_days, None
    if basis_days >= thresholds["overdue"]:
        return "overdue", age_days, idle_days, action.created_at + timedelta(days=thresholds["critical"])
    if basis_days >= thresholds["aging"]:
        return "aging", age_days, idle_days, action.created_at + timedelta(days=thresholds["overdue"])
    return "fresh", age_days, idle_days, action.created_at + timedelta(days=thresholds["aging"])


def _reason(action: ResearchReviewAction, state: str, age_days: int, idle_days: int, days_overdue: int) -> str:
    if days_overdue:
        return f"The follow-up is {days_overdue} day(s) past its due date."
    if state == "critical":
        return f"The {action.priority} follow-up has remained active for {age_days} day(s) and idle for {idle_days} day(s)."
    if state == "overdue":
        return f"The {action.priority} follow-up exceeded its deterministic review window."
    if state == "aging":
        return f"The {action.priority} follow-up is approaching its overdue threshold."
    return "The follow-up remains within its expected review window."


def _recommended_action(action: ResearchReviewAction, state: str) -> str:
    if state == "critical":
        return "Review immediately, record the blocking reason, and either advance, defer with justification, or resolve after verification."
    if state == "overdue":
        return "Review today and update status, due date, or owner notes with the next concrete research step."
    if state == "aging":
        return "Confirm ownership and schedule the next evidence-review step before the overdue threshold."
    if action.status == "blocked":
        return "Document the blocker and define the condition required to resume research review."
    return "Continue the planned research review and keep status and notes current."


@router.get("/evidence-remediation/escalations", response_model=RemediationEscalationInventory)
def list_saved_record_remediation_escalations(
    project_id: int | None = Query(default=None),
    escalation_state: RemediationEscalationState | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RemediationEscalationInventory:
    query = select(ResearchReviewAction).where(
        ResearchReviewAction.owner_id == current_user.id,
        ResearchReviewAction.status.notin_(_TERMINAL),
        ResearchReviewAction.governing_rule.startswith("saved_record_"),
    )
    if project_id is not None:
        query = query.where(ResearchReviewAction.project_id == project_id)
    actions = list(db.scalars(query).all())
    now = datetime.utcnow()
    items: list[RemediationEscalationItem] = []
    for action in actions:
        state, age_days, idle_days, next_escalation_at = _state_for(action, now)
        days_overdue = max(0, (now - action.due_at).days) if action.due_at and action.due_at < now else 0
        items.append(
            RemediationEscalationItem(
                follow_up_id=action.id,
                project_id=action.project_id,
                evidence_id=action.evidence_id,
                action_key=action.action_key,
                governing_rule=action.governing_rule,
                status=action.status,
                priority=action.priority,
                escalation_state=state,
                age_days=age_days,
                idle_days=idle_days,
                due_at=action.due_at,
                days_overdue=days_overdue,
                next_escalation_at=next_escalation_at,
                escalation_reason=_reason(action, state, age_days, idle_days, days_overdue),
                recommended_owner_action=_recommended_action(action, state),
                created_at=action.created_at,
                updated_at=action.updated_at,
            )
        )
    if escalation_state is not None:
        items = [item for item in items if item.escalation_state == escalation_state]
    items.sort(
        key=lambda item: (
            _STATE_RANK[item.escalation_state],
            item.due_at is None,
            item.due_at or datetime.max,
            -item.age_days,
            item.follow_up_id,
        )
    )
    counts = {state: 0 for state in ("fresh", "aging", "overdue", "critical")}
    for item in items:
        counts[item.escalation_state] += 1
    return RemediationEscalationInventory(
        project_id=project_id,
        escalation_state=escalation_state,
        total=len(items),
        by_state=counts,
        items=items,
        disclaimer=DISCLAIMER,
    )
