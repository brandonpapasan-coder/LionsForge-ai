from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.evidence import ResearchReviewAction, ResearchReviewActionHistory
from app.models.research_project import ResearchProject
from app.models.user import User
from app.schemas.research_follow_up_tracker import (
    FollowUpActionItem,
    FollowUpActionQueue,
    FollowUpActionUpdate,
    FollowUpHistoryItem,
)

router = APIRouter()
DISCLAIMER = "Follow-up actions manage research review workflow only. They do not modify evidence or certify claim truth, accuracy, professional competence, financial outcomes, or predictive value."
TERMINAL = {"resolved", "dismissed"}
TRANSITIONS = {
    "open": {"acknowledged", "in_progress", "blocked", "deferred", "resolved", "dismissed"},
    "acknowledged": {"open", "in_progress", "blocked", "deferred", "resolved", "dismissed"},
    "in_progress": {"open", "blocked", "deferred", "resolved", "dismissed"},
    "blocked": {"open", "in_progress", "deferred", "resolved", "dismissed"},
    "deferred": {"open", "acknowledged", "in_progress", "blocked", "resolved", "dismissed"},
    "resolved": {"open", "in_progress"},
    "dismissed": {"open"},
}
PRIORITY_RANK = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
IMPACT_RANK = {"high_attention": 0, "review_required": 1, "informational": 2}


def _item(action: ResearchReviewAction, history: list[ResearchReviewActionHistory]) -> FollowUpActionItem:
    now = datetime.utcnow()
    overdue = action.due_at is not None and action.due_at < now and action.status not in TERMINAL
    urgency_rank = PRIORITY_RANK[action.priority] * 100 + IMPACT_RANK[action.impact_level] * 10 + (0 if overdue else 1)
    return FollowUpActionItem(
        id=action.id,
        project_id=action.project_id,
        evidence_id=action.evidence_id,
        action_key=action.action_key,
        impact_level=action.impact_level,
        governing_rule=action.governing_rule,
        reason=action.reason,
        action_text=action.action_text,
        supporting_event_ids=sorted(action.supporting_event_ids),
        status=action.status,
        priority=action.priority,
        due_at=action.due_at,
        owner_notes=action.owner_notes,
        resolution_notes=action.resolution_notes,
        resolved_at=action.resolved_at,
        overdue=overdue,
        urgency_rank=urgency_rank,
        created_at=action.created_at,
        updated_at=action.updated_at,
        history=[FollowUpHistoryItem(id=item.id, previous_status=item.previous_status, new_status=item.new_status, note=item.note, created_at=item.created_at) for item in history],
    )


@router.get("/projects/{project_id}", response_model=FollowUpActionQueue)
def list_follow_up_actions(
    project_id: int,
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    overdue_only: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FollowUpActionQueue:
    project = db.scalar(select(ResearchProject).where(ResearchProject.id == project_id, ResearchProject.owner_id == current_user.id))
    if project is None:
        raise HTTPException(status_code=404, detail="Research project not found")
    actions = list(db.scalars(select(ResearchReviewAction).where(ResearchReviewAction.owner_id == current_user.id, ResearchReviewAction.project_id == project_id)).all())
    histories = [] if not actions else list(db.scalars(select(ResearchReviewActionHistory).where(ResearchReviewActionHistory.owner_id == current_user.id, ResearchReviewActionHistory.action_id.in_([item.id for item in actions])).order_by(ResearchReviewActionHistory.created_at, ResearchReviewActionHistory.id)).all())
    grouped: dict[int, list[ResearchReviewActionHistory]] = defaultdict(list)
    for item in histories:
        grouped[item.action_id].append(item)
    items = [_item(action, grouped[action.id]) for action in actions]
    if status:
        items = [item for item in items if item.status == status]
    if priority:
        items = [item for item in items if item.priority == priority]
    if overdue_only:
        items = [item for item in items if item.overdue]
    items.sort(key=lambda item: (item.status in TERMINAL, item.urgency_rank, item.due_at is None, item.due_at or datetime.max, item.id))
    return FollowUpActionQueue(project_id=project_id, total=len(items), overdue=sum(item.overdue for item in items), blocked=sum(item.status == "blocked" for item in items), actions=items, disclaimer=DISCLAIMER)


@router.patch("/actions/{action_id}", response_model=FollowUpActionItem)
def update_follow_up_action(
    action_id: int,
    request: FollowUpActionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FollowUpActionItem:
    if not request.confirmed:
        raise HTTPException(status_code=400, detail="Explicit confirmation is required")
    action = db.scalar(select(ResearchReviewAction).where(ResearchReviewAction.id == action_id, ResearchReviewAction.owner_id == current_user.id))
    if action is None:
        raise HTTPException(status_code=404, detail="Follow-up action not found")
    now = datetime.utcnow()
    changed = False
    if request.status is not None and request.status != action.status:
        if request.status not in TRANSITIONS.get(action.status, set()):
            raise HTTPException(status_code=409, detail=f"Invalid transition from {action.status} to {request.status}")
        previous = action.status
        action.status = request.status
        action.resolved_at = now if request.status in TERMINAL else None
        db.add(ResearchReviewActionHistory(action_id=action.id, owner_id=current_user.id, previous_status=previous, new_status=request.status, note=request.note))
        changed = True
    for field in ("priority", "due_at", "owner_notes", "resolution_notes"):
        value = getattr(request, field)
        if value is not None and value != getattr(action, field):
            setattr(action, field, value)
            changed = True
    if action.status == "resolved" and not (action.resolution_notes or "").strip():
        raise HTTPException(status_code=422, detail="Resolution notes are required when resolving an action")
    if changed:
        action.updated_at = now
        db.commit()
        db.refresh(action)
    history = list(db.scalars(select(ResearchReviewActionHistory).where(ResearchReviewActionHistory.owner_id == current_user.id, ResearchReviewActionHistory.action_id == action.id).order_by(ResearchReviewActionHistory.created_at, ResearchReviewActionHistory.id)).all())
    return _item(action, history)
