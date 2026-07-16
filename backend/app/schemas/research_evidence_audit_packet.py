from datetime import datetime
from typing import Literal

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


class AuditPacketVerificationCheck(BaseModel):
    code: str
    passed: bool
    message: str


class ResearchEvidenceAuditPacketVerification(BaseModel):
    valid: bool
    schema_version_supported: bool
    integrity_matches: bool
    chronology_valid: bool
    supersession_references_valid: bool
    computed_sha256: str
    checks: list[AuditPacketVerificationCheck]
    disclaimer: str


class ResearchEvidenceAuditPacketComparisonRequest(BaseModel):
    baseline: ResearchEvidenceAuditPacket
    current: ResearchEvidenceAuditPacket


class AuditPacketComparisonSummary(BaseModel):
    added: int
    removed: int
    changed: int
    unchanged: int
    project_changed: bool
    summary_changed: bool


class AuditPacketEntryChange(BaseModel):
    event_id: str
    classification: Literal["added", "removed", "changed", "unchanged"]
    event_type: str
    evidence_id: int
    changed_fields: list[str]
    explanation: str
    baseline: ProvenanceLedgerEntry | None = None
    current: ProvenanceLedgerEntry | None = None


class ResearchEvidenceAuditPacketComparison(BaseModel):
    comparable: bool
    baseline_verification: ResearchEvidenceAuditPacketVerification
    current_verification: ResearchEvidenceAuditPacketVerification
    summary: AuditPacketComparisonSummary
    changes: list[AuditPacketEntryChange]
    project_changes: list[str]
    summary_changes: list[str]
    disclaimer: str
