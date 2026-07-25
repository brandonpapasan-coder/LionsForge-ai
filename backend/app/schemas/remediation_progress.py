from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

ProgressStatus = Literal[
    "not_started",
    "in_progress",
    "blocked",
    "ready_for_review",
    "dismissed",
]
ActionType = Literal[
    "resolve_contradiction",
    "collect_direct_evidence",
    "attach_initial_evidence",
    "refresh_human_review",
]


class RemediationProgressUpdate(BaseModel):
    status: ProgressStatus
    notes: str | None = Field(default=None, max_length=8000)

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class RemediationCurrentAction(BaseModel):
    action_type: ActionType
    priority: int = Field(ge=1)
    rationale: str
    completion_criteria: list[str]
    generated_from_stored_state_at: datetime


class RemediationProgressEntry(BaseModel):
    claim_id: int
    claim_sequence: int | None
    statement: str
    status: ProgressStatus
    notes: str | None
    authorship: Literal["user_authored"] = "user_authored"
    is_stale: bool
    stale_reasons: list[str]
    action_type_snapshot: ActionType
    priority_snapshot: int = Field(ge=1)
    plan_generated_at_snapshot: datetime
    current_action: RemediationCurrentAction | None
    created_at: datetime
    updated_at: datetime


class RemediationProgressLedger(BaseModel):
    contract_version: str = "1.0"
    investigation_id: int
    title: str
    status: Literal["empty", "active"]
    entries: list[RemediationProgressEntry]
    generated_from: Literal["user_progress_and_current_remediation_plan"] = (
        "user_progress_and_current_remediation_plan"
    )
    interpretation_notice: str = (
        "Progress statuses and notes are user-authored workflow records. They do not change "
        "deterministic validation or remediation state and do not establish truth, completion, "
        "or resolution."
    )


class RemediationProgressHistoryEvent(BaseModel):
    event_id: int
    claim_id: int
    status: ProgressStatus
    notes: str | None
    authorship: Literal["user_authored"] = "user_authored"
    action_type_snapshot: ActionType
    priority_snapshot: int = Field(ge=1)
    plan_generated_at_snapshot: datetime
    recorded_at: datetime


class RemediationProgressHistory(BaseModel):
    contract_version: str = "1.0"
    investigation_id: int
    claim_id: int
    status: Literal["empty", "active"]
    events: list[RemediationProgressHistoryEvent]
    generated_from: Literal["append_only_user_progress_history"] = (
        "append_only_user_progress_history"
    )
    interpretation_notice: str = (
        "History events are append-only snapshots of user-authored workflow state. They do not "
        "change deterministic validation or remediation state and do not establish truth, "
        "completion, or resolution."
    )
