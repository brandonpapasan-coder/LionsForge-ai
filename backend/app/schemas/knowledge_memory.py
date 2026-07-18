from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MemoryStatus = Literal["provisional", "validated", "contested", "superseded", "archived"]
EvidenceHealthClassification = Literal[
    "strong",
    "adequate",
    "weak",
    "contested",
    "unavailable",
    "unsupported",
]
EvidenceRemediationActionType = Literal[
    "restore_evidence",
    "resolve_contradiction",
    "review_evidence",
    "add_direct_support",
    "improve_source_quality",
]
EvidenceRemediationPriority = Literal["urgent", "high", "normal", "low"]
EvidenceRemediationVerificationStatus = Literal[
    "unresolved",
    "partially_satisfied",
    "ready_for_resolution",
]
UserAuthoredMemoryCategory = Literal[
    "research_preference",
    "research_context",
    "learning_goal",
    "mentor_preference",
    "mastery_signal",
    "misconception",
]


class KnowledgeMemoryCreate(BaseModel):
    project_id: int
    statement: str = Field(min_length=1, max_length=4000)
    summary: str = Field(min_length=1, max_length=1000)
    category: UserAuthoredMemoryCategory
    confidence: float = Field(default=0.5, ge=0, le=1)
    source_evidence_ids: list[int] = Field(default_factory=list)
    provenance: dict = Field(default_factory=dict)


class KnowledgeMemoryUpdate(BaseModel):
    statement: str | None = Field(default=None, min_length=1)
    summary: str | None = Field(default=None, min_length=1)
    category: str | None = Field(default=None, min_length=1, max_length=64)
    status: MemoryStatus | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    source_evidence_ids: list[int] | None = None


class KnowledgeMemoryRevisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    revision_number: int
    statement: str
    summary: str
    category: str
    status: str
    confidence: float
    source_evidence_ids: list[int]
    provenance: dict
    created_at: datetime


class KnowledgeMemoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    mission_id: int | None
    snapshot_id: int | None
    fingerprint: str
    statement: str
    summary: str
    category: str
    status: str
    confidence: float
    source_evidence_ids: list[int]
    provenance: dict
    superseded_by_id: int | None
    revision_number: int
    created_at: datetime
    updated_at: datetime
    revisions: list[KnowledgeMemoryRevisionRead] = Field(default_factory=list)


class KnowledgeMemoryEvidenceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int | None
    source_url: str | None
    source_title: str
    publisher: str | None
    author: str | None
    published_at: datetime | None
    source_type: str
    claim: str
    excerpt: str
    stance: str
    credibility_score: float
    freshness_score: float
    confidence_score: float
    validation_status: str


class KnowledgeMemoryEvidenceHealth(BaseModel):
    classification: EvidenceHealthClassification
    total_count: int
    available_count: int
    unavailable_count: int
    approved_count: int
    needs_review_count: int
    supporting_count: int
    contradicting_count: int
    average_credibility: float | None
    average_freshness: float | None
    average_confidence: float | None
    reasons: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)


class KnowledgeMemoryEvidenceTrace(BaseModel):
    memory_id: int
    requested_evidence_ids: list[int]
    evidence: list[KnowledgeMemoryEvidenceItem]
    unavailable_evidence_ids: list[int]
    health: KnowledgeMemoryEvidenceHealth


class KnowledgeMemoryEvidenceHealthInventoryItem(BaseModel):
    memory_id: int
    project_id: int
    summary: str
    statement: str
    category: str
    status: str
    confidence: float
    updated_at: datetime
    health: KnowledgeMemoryEvidenceHealth


class KnowledgeMemoryEvidenceHealthInventory(BaseModel):
    project_id: int | None
    classification: EvidenceHealthClassification | None
    total_count: int
    by_classification: dict[str, int]
    items: list[KnowledgeMemoryEvidenceHealthInventoryItem]


class KnowledgeMemoryEvidenceRemediationAction(BaseModel):
    action_key: str
    action_type: EvidenceRemediationActionType
    priority: EvidenceRemediationPriority
    rationale: str
    action_text: str
    related_evidence_ids: list[int] = Field(default_factory=list)
    completion_criteria: list[str] = Field(default_factory=list)
    existing_follow_up_id: int | None = None


class KnowledgeMemoryEvidenceRemediationPlan(BaseModel):
    memory_id: int
    project_id: int
    health: KnowledgeMemoryEvidenceHealth
    total_actions: int
    open_follow_up_count: int
    actions: list[KnowledgeMemoryEvidenceRemediationAction]


class KnowledgeMemoryEvidenceRemediationCreateRequest(BaseModel):
    action_key: str = Field(min_length=1, max_length=64)
    confirmed: bool = False


class KnowledgeMemoryEvidenceRemediationCreateResult(BaseModel):
    created: bool
    follow_up_id: int
    action_key: str


class KnowledgeMemoryEvidenceRemediationCriterionVerification(BaseModel):
    criterion: str
    passed: bool
    explanation: str
    supporting_evidence_ids: list[int] = Field(default_factory=list)


class KnowledgeMemoryEvidenceRemediationActionVerification(BaseModel):
    action_key: str
    action_type: EvidenceRemediationActionType
    follow_up_id: int | None
    follow_up_status: str | None
    status: EvidenceRemediationVerificationStatus
    passed_count: int
    total_count: int
    criteria: list[KnowledgeMemoryEvidenceRemediationCriterionVerification]


class KnowledgeMemoryEvidenceRemediationVerification(BaseModel):
    memory_id: int
    project_id: int
    total_actions: int
    ready_for_resolution_count: int
    actions: list[KnowledgeMemoryEvidenceRemediationActionVerification]


class KnowledgeMemoryEvidenceRemediationResolveRequest(BaseModel):
    action_key: str = Field(min_length=1, max_length=64)
    resolution_notes: str = Field(min_length=1, max_length=4000)
    confirmed: bool = False


class KnowledgeMemoryEvidenceRemediationResolveResult(BaseModel):
    resolved: bool
    follow_up_id: int
    action_key: str
    status: str
    resolved_at: datetime


class KnowledgeMemoryPromotionResult(BaseModel):
    memories: list[KnowledgeMemoryRead]
    created_count: int
    reused_count: int


class KnowledgeMemoryControlSummary(BaseModel):
    project_id: int | None
    total_count: int
    active_count: int
    archived_count: int
    user_authored_count: int
    research_generated_count: int
    revision_count: int
    by_status: dict[str, int]
    by_category: dict[str, int]
    available_controls: list[str]


class KnowledgeMemorySynthesis(BaseModel):
    project_id: int
    validated: list[KnowledgeMemoryRead]
    provisional: list[KnowledgeMemoryRead]
    contested: list[KnowledgeMemoryRead]
    superseded: list[KnowledgeMemoryRead]
    agreements: list[str]
    contradictions: list[str]
    unresolved_questions: list[str]
