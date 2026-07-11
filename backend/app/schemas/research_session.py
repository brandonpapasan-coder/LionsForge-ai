from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ResearchSessionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    objective: str | None = None
    context: dict = Field(default_factory=dict)


class ResearchSessionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    objective: str | None = None
    summary: str | None = None
    status: str | None = Field(default=None, pattern="^(active|paused|completed|archived)$")
    context: dict | None = None


class ResearchSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    objective: str | None
    summary: str | None
    status: str
    context: dict
    created_at: datetime
    updated_at: datetime
