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
    contract_version: Literal["1.0"] = "1.0"
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


class ReviewQueueSnapshotComparison(BaseModel):
    contract_version: Literal["1.0"] = "1.0"
    artifact_type: Literal["cross_investigation_review_queue_snapshot_comparison"] = (
        "cross_investigation_review_queue_snapshot_comparison"
    )
    prior_content_sha256: str
    current_content_sha256: str
    added_items: list[ReviewQueueItem]
    removed_items: list[ReviewQueueItem]
    unchanged_items: list[ReviewQueueItem]
    prior_reason_counts: dict[str, int]
    current_reason_counts: dict[str, int]
    reason_count_deltas: dict[str, int]
    prior_investigation_count: int
    current_investigation_count: int
    investigation_count_delta: int
    interpretation_notice: str = (
        "This comparison describes changes in stored workflow state only. Snapshot digests "
        "verify artifact integrity only and do not establish truth, confidence, importance, "
        "urgency, risk, resolution, validation evidence, advice, or recommended action."
    )


class ReviewQueueComparisonReportUnsigned(BaseModel):
    contract_version: Literal["1.0"] = "1.0"
    artifact_type: Literal["cross_investigation_review_queue_comparison_report"] = (
        "cross_investigation_review_queue_comparison_report"
    )
    comparison: ReviewQueueSnapshotComparison
    generated_from: Literal["verified_snapshot_comparison"] = (
        "verified_snapshot_comparison"
    )
    interpretation_notice: str = (
        "This report preserves a deterministic comparison of stored workflow state. Its digest "
        "verifies report integrity only and does not establish truth, confidence, importance, "
        "urgency, risk, resolution, validation evidence, advice, or recommended action."
    )


class ReviewQueueComparisonReport(ReviewQueueComparisonReportUnsigned):
    generated_at: datetime
    content_sha256: str


class ReviewQueueComparisonReportVerification(BaseModel):
    contract_version: Literal["1.0"] = "1.0"
    artifact_type: Literal["cross_investigation_review_queue_comparison_report_verification"] = (
        "cross_investigation_review_queue_comparison_report_verification"
    )
    valid: Literal[True] = True
    supplied_content_sha256: str
    recomputed_content_sha256: str
    prior_content_sha256: str
    current_content_sha256: str
    added_item_count: int
    removed_item_count: int
    unchanged_item_count: int
    reason_count_deltas: dict[str, int]
    investigation_count_delta: int
    current_state_checked: Literal[False] = False
    interpretation_notice: str = (
        "Verification confirms this uploaded report's contract and canonical digest only. It "
        "does not establish truth, confidence, importance, urgency, risk, resolution, validation "
        "evidence, advice, recommended action, or that the preserved comparison matches current "
        "queue state."
    )
