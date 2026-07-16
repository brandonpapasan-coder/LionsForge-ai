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


class ResearchEvidenceChangeImpactRequest(BaseModel):
    baseline: ResearchEvidenceAuditPacket
    current: ResearchEvidenceAuditPacket


class ResearchEvidenceImpactItem(BaseModel):
    impact_level: Literal["high_attention", "review_required", "informational"]
    evidence_id: int
    event_ids: list[str]
    rules: list[str]
    reasons: list[str]
    follow_up_actions: list[str]


class ResearchEvidenceChangeImpactSummary(BaseModel):
    high_attention: int
    review_required: int
    informational: int
    material_change: bool


class ResearchEvidenceChangeImpactAssessment(BaseModel):
    comparable: bool
    summary: ResearchEvidenceChangeImpactSummary
    impacts: list[ResearchEvidenceImpactItem]
    global_actions: list[str]
    comparison: ResearchEvidenceAuditPacketComparison
    disclaimer: str


ReviewActionStatus = Literal["open", "acknowledged", "deferred", "resolved"]


class ResearchReviewActionGenerateRequest(BaseModel):
    baseline: ResearchEvidenceAuditPacket
    current: ResearchEvidenceAuditPacket


class ResearchReviewActionHistoryItem(BaseModel):
    id: int
    previous_status: ReviewActionStatus
    new_status: ReviewActionStatus
    note: str | None
    created_at: datetime


class ResearchReviewActionItem(BaseModel):
    id: int
    project_id: int
    evidence_id: int
    action_key: str
    impact_level: Literal["high_attention", "review_required", "informational"]
    governing_rule: str
    reason: str
    action_text: str
    supporting_event_ids: list[str]
    status: ReviewActionStatus
    created_at: datetime
    updated_at: datetime
    history: list[ResearchReviewActionHistoryItem] = []


class ResearchReviewActionPlan(BaseModel):
    project_id: int
    generated: int
    existing: int
    actions: list[ResearchReviewActionItem]
    disclaimer: str


class ResearchReviewActionTransitionRequest(BaseModel):
    status: ReviewActionStatus
    confirmed: bool
    note: str | None = None
