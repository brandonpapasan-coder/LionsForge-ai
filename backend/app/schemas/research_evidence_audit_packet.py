from datetime import datetime

from pydantic import BaseModel

from app.schemas.research_evidence_provenance import ProvenanceLedgerEntry, ProvenanceLedgerSummary


class AuditPacketProject(BaseModel):
    id: int
    title: str
    description: str | None
    objective: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class ResearchEvidenceAuditPacket(BaseModel):
    schema_version: str = "1.0"
    generated_at: datetime
    project: AuditPacketProject
    summary: ProvenanceLedgerSummary
    entries: list[ProvenanceLedgerEntry]
    disclaimer: str
    content_sha256: str
