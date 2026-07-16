from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

PacketConclusionStatus = Literal["missing", "draft", "revised", "finalized"]
ReadinessState = Literal["blocked", "needs_review", "ready_for_user_conclusion"]


class ConclusionPacketEvidence(BaseModel):
    id: int
    source_title: str
    source_url: str | None
    publisher: str | None
    author: str | None
    published_at: datetime | None
    source_type: str
    claim: str
    excerpt: str
    stance: str
    validation_status: str
    reviewer_notes: str | None
    provenance: dict = Field(default_factory=dict)


class ConclusionPacketRevision(BaseModel):
    revision_number: int
    conclusion_text: str
    evidence_ids: list[int]
    revision_note: str | None
    status: Literal["draft", "revised", "finalized"]
    created_at: datetime


class ConclusionPacketReadinessCheck(BaseModel):
    code: str
    level: Literal["blocking", "caution", "informational"]
    passed: bool
    message: str
    evidence_ids: list[int] = Field(default_factory=list)
    action_ids: list[int] = Field(default_factory=list)
    event_ids: list[str] = Field(default_factory=list)
    governing_rules: list[str] = Field(default_factory=list)


class ConclusionPacketReadiness(BaseModel):
    state: ReadinessState
    evidence_count: int
    blocking_count: int
    caution_count: int
    checks: list[ConclusionPacketReadinessCheck]
    next_steps: list[str]
    disclaimer: str


class ResearchConclusionPacketContent(BaseModel):
    schema_version: str = "1.0"
    project_id: int
    project_title: str
    conclusion_status: PacketConclusionStatus
    conclusion_text: str
    evidence_ids: list[int]
    evidence: list[ConclusionPacketEvidence]
    revisions: list[ConclusionPacketRevision]
    readiness: ConclusionPacketReadiness
    disclaimer: str


class ResearchConclusionExportPacket(BaseModel):
    content_sha256: str
    generated_at: datetime
    content: ResearchConclusionPacketContent
