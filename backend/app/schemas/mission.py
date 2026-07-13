from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MissionCreate(BaseModel):
    project_id: int
    title: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=1)
    success_criteria: list[str] = Field(default_factory=list)


class MissionStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    step_order: int
    key: str
    title: str
    status: str
    attempt: int
    inputs: dict
    outputs: dict
    blocking_reason: str | None
    methodology_version: str
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class MissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    objective: str
    success_criteria: list[str]
    status: str
    current_step_order: int
    final_snapshot_id: int | None
    blocking_reason: str | None
    methodology_version: str
    created_at: datetime
    updated_at: datetime
    steps: list[MissionStepRead] = Field(default_factory=list)
