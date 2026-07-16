from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.research_conclusion_export_packet import ResearchConclusionPacketContent

DefensePacketStatus = Literal["missing", "incomplete", "complete"]


class DefensePacketRevision(BaseModel):
    revision_number: int
    conclusion_revision_number: int | None
    evidence_ids: list[int]
    evidence_coverage: str
    strongest_counterargument: str
    known_limitations: str
    unresolved_questions: str
    confidence_rationale: str
    status: Literal["incomplete", "complete"]
    missing_sections: list[str]
    revision_note: str | None
    created_at: datetime


class DefensePacketContent(BaseModel):
    status: DefensePacketStatus
    conclusion_revision_number: int | None
    evidence_ids: list[int] = Field(default_factory=list)
    evidence_coverage: str = ""
    strongest_counterargument: str = ""
    known_limitations: str = ""
    unresolved_questions: str = ""
    confidence_rationale: str = ""
    missing_sections: list[str] = Field(default_factory=list)
    revision_count: int = 0
    revisions: list[DefensePacketRevision] = Field(default_factory=list)
    disclaimer: str


class ResearchConclusionDefensePacketContent(BaseModel):
    schema_version: str = "1.0"
    conclusion: ResearchConclusionPacketContent
    defense: DefensePacketContent
    disclaimer: str


class ResearchConclusionDefenseExportPacket(BaseModel):
    content_sha256: str
    generated_at: datetime
    content: ResearchConclusionDefensePacketContent
