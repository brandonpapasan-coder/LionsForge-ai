from datetime import datetime

from pydantic import BaseModel


class ProvenanceLedgerEntry(BaseModel):
    event_id: str
    event_type: str
    evidence_id: int
    project_id: int | None
    source_title: str
    source_type: str
    source_url: str | None = None
    publisher: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    fingerprint: str = ""
    credibility_score: float = 0.0
    freshness_score: float = 0.0
    confidence_score: float = 0.0
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
