from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

FollowUpStatus = Literal["open", "acknowledged", "in_progress", "blocked", "deferred", "resolved", "dismissed"]
FollowUpPriority = Literal["low", "normal", "high", "urgent"]
RemediationEscalationState = Literal["fresh", "aging", "overdue", "critical"]


class FollowUpActionUpdate(BaseModel):
    status: FollowUpStatus | None = None
    priority: FollowUpPriority | None = None
    due_at: datetime | None = None
    owner_notes: str | None = Field(default=None, max_length=4000)
    resolution_notes: str | None = Field(default=None, max_length=4000)
    note: str | None = Field(default=None, max_length=2000)
    confirmed: bool = False


class FollowUpHistoryItem(BaseModel):
    id: int
    previous_status: FollowUpStatus
    new_status: FollowUpStatus
    note: str | None
    created_at: datetime


class FollowUpActionItem(BaseModel):
    id: int
    project_id: int
    evidence_id: int
    action_key: str
    impact_level: Literal["high_attention", "review_required", "informational"]
    governing_rule: str
    reason: str
    action_text: str
    supporting_event_ids: list[str]
    status: FollowUpStatus
    priority: FollowUpPriority
    due_at: datetime | None
    owner_notes: str | None
    resolution_notes: str | None
    resolved_at: datetime | None
    overdue: bool
    urgency_rank: int
    created_at: datetime
    updated_at: datetime
    history: list[FollowUpHistoryItem] = []


class FollowUpActionQueue(BaseModel):
    project_id: int
    total: int
    overdue: int
    blocked: int
    actions: list[FollowUpActionItem]
    disclaimer: str


class RemediationEscalationItem(BaseModel):
    follow_up_id: int
    project_id: int
    evidence_id: int
    action_key: str
    governing_rule: str
    status: FollowUpStatus
    priority: FollowUpPriority
    escalation_state: RemediationEscalationState
    age_days: int
    idle_days: int
    due_at: datetime | None
    days_overdue: int
    next_escalation_at: datetime | None
    escalation_reason: str
    recommended_owner_action: str
    created_at: datetime
    updated_at: datetime


class RemediationEscalationInventory(BaseModel):
    project_id: int | None
    escalation_state: RemediationEscalationState | None
    total: int
    by_state: dict[str, int]
    items: list[RemediationEscalationItem]
    disclaimer: str
