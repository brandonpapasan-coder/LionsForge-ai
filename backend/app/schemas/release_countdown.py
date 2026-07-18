from typing import Literal

from pydantic import BaseModel


CheckpointState = Literal["complete", "remaining", "blocked"]


class ReleaseCountdownCheckpoint(BaseModel):
    key: str
    label: str
    state: CheckpointState
    external: bool
    issue_number: int | None = None


class ReleaseCountdownPhase(BaseModel):
    key: str
    label: str
    weight: int
    completed_points: int
    completion_percent: int
    state: CheckpointState
    checkpoints: list[ReleaseCountdownCheckpoint]


class ReleaseCountdownSummary(BaseModel):
    overall_completion_percent: int
    completed_points: int
    remaining_points: int
    total_points: int
    completed_checkpoints: int
    remaining_checkpoints: int
    blocked_checkpoints: int
    external_checkpoints: int
    remaining_milestones: int
    current_blocker: str | None
    next_action: str | None
    phases: list[ReleaseCountdownPhase]
    disclaimer: str
