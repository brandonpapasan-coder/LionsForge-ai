from datetime import datetime
from typing import Literal

from pydantic import BaseModel

ReviewReason = Literal[
    "stale_validation",
    "missing_validation",
    "unresolved_contradiction",
    "blocked_remediation",
    "remediation_ready_for_review",
]


class ReviewQueueItem(BaseModel):
    item_key: str
    investigation_id: int
    investigation_title: str
    investigation_status: str
    claim_id: int
    claim_statement: str
    reason_type: ReviewReason
    workflow_priority: int
    reason: str
    stored_inputs: list[str]
    latest_relevant_at: datetime
    source_tables: list[str]
    source_record_ids: list[int]


class CrossInvestigationReviewQueue(BaseModel):
    contract_version: str = "1.0"
    status: Literal["empty", "active"]
    item_count: int
    items: list[ReviewQueueItem]
    generated_from: Literal["stored_owner_investigation_records"] = (
        "stored_owner_investigation_records"
    )
    interpretation_notice: str = (
        "This queue uses deterministic workflow rules over stored records. Ranking does not "
        "establish truth, confidence, importance, urgency, risk, or recommended action."
    )


class ReviewQueueSnapshotUnsigned(BaseModel):
    contract_version: str = "1.0"
    artifact_type: Literal["cross_investigation_review_queue_snapshot"] = (
        "cross_investigation_review_queue_snapshot"
    )
    queue: CrossInvestigationReviewQueue
    reason_counts: dict[str, int]
    investigation_count: int
    generated_from: Literal["canonical_owner_review_queue"] = (
        "canonical_owner_review_queue"
    )
    interpretation_notice: str = (
        "This snapshot preserves stored workflow conditions. Its digest verifies artifact "
        "integrity only and does not establish truth, confidence, importance, urgency, risk, "
        "resolution, or recommended action."
    )


class ReviewQueueSnapshot(ReviewQueueSnapshotUnsigned):
    generated_at: datetime
    content_sha256: str
