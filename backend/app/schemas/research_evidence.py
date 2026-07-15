from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ResearchEvidenceCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    summary: str | None = None
    source_type: str = Field(default="note", min_length=1, max_length=32)
    source_reference: str | None = None
    tags: list[str] = Field(default_factory=list)


class ResearchEvidenceUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    summary: str | None = None
    source_type: str | None = Field(default=None, min_length=1, max_length=32)
    source_reference: str | None = None
    tags: list[str] | None = None
    status: str | None = Field(default=None, pattern="^(active|archived)$")


class ResearchEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    session_id: int | None
    title: str
    summary: str | None
    source_type: str
    source_reference: str | None
    tags: list[str]
    status: str
    created_at: datetime
    updated_at: datetime
