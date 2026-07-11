from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ResearchProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str | None = None
    objective: str | None = None
    context: dict = Field(default_factory=dict)


class ResearchProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    objective: str | None = None
    status: str | None = Field(default=None, pattern="^(active|archived|completed)$")
    context: dict | None = None


class ResearchProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    objective: str | None
    status: str
    context: dict
    created_at: datetime
    updated_at: datetime
