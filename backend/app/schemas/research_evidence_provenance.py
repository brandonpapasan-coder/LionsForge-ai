from datetime import datetime

from pydantic import BaseModel


class ProvenanceLedgerEntry(BaseModel):
    event_id: str
    event_type: str
    evidence_id: int
    project_id: int | None
    source_title: str
    source_type: str
    claim: str
    validation_status: str
    contradiction_key: str | None
    supersedes_evidence_id: int | None = None
    reviewer_notes: str | None = None
    warning: str | None = None
    occurred_at: datetime


class ProvenanceLedgerSummary(BaseModel):
    total_evidence: int
    total_events: int
    unresolved_contradictions: int
    superseded_claims: int
    missing_source_metadata: int


class ResearchEvidenceProvenanceLedger(BaseModel):
    summary: ProvenanceLedgerSummary
    entries: list[ProvenanceLedgerEntry]
    disclaimer: str
