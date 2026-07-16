from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

ConclusionStatus = Literal["draft", "revised", "finalized"]


class ResearchConclusionDraftUpdate(BaseModel):
    conclusion_text: str = Field(default="", max_length=20000)
    evidence_ids: list[int] = Field(default_factory=list)
    revision_note: str | None = Field(default=None, max_length=1000)
    finalize: bool = False
    confirmed: bool = False

    @field_validator("evidence_ids")
    @classmethod
    def unique_evidence_ids(cls, value: list[int]) -> list[int]:
        return list(dict.fromkeys(value))


class ResearchConclusionRevision(BaseModel):
    id: int
    conclusion_id: int
    revision_number: int
    conclusion_text: str
    evidence_ids: list[int]
    revision_note: str | None
    status: ConclusionStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class ResearchConclusionWorkspace(BaseModel):
    id: int | None
    project_id: int
    status: ConclusionStatus
    conclusion_text: str
    evidence_ids: list[int]
    revision_count: int
    finalized_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None
    revisions: list[ResearchConclusionRevision]
    disclaimer: str
