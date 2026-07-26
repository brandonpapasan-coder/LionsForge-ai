from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from app.api.deps import get_current_user
from app.api.routes.review_queue_snapshot import _validated_receipt, _verified_report
from app.models.user import User
from app.schemas.review_queue import (
    ReviewQueueArtifactIntegrityResult,
    ReviewQueueComparisonReport,
    ReviewQueueComparisonVerificationReceipt,
)

router = APIRouter()

REPORT_ARTIFACT = "cross_investigation_review_queue_comparison_report"
RECEIPT_ARTIFACT = (
    "cross_investigation_review_queue_comparison_verification_receipt"
)


def _validate_supported_artifact(payload: dict[str, Any]) -> ReviewQueueArtifactIntegrityResult:
    artifact_type = payload.get("artifact_type")
    if artifact_type == REPORT_ARTIFACT:
        try:
            report = ReviewQueueComparisonReport.model_validate(payload)
        except ValidationError as exc:
            raise HTTPException(
                status_code=422,
                detail="Comparison report contract is invalid or unsupported",
            ) from exc
        return ReviewQueueArtifactIntegrityResult(
            detected_artifact_type=REPORT_ARTIFACT,
            validation=_verified_report(report),
        )

    if artifact_type == RECEIPT_ARTIFACT:
        try:
            receipt = ReviewQueueComparisonVerificationReceipt.model_validate(payload)
        except ValidationError as exc:
            raise HTTPException(
                status_code=422,
                detail="Verification receipt contract is invalid or unsupported",
            ) from exc
        return ReviewQueueArtifactIntegrityResult(
            detected_artifact_type=RECEIPT_ARTIFACT,
            validation=_validated_receipt(receipt),
        )

    if artifact_type is None:
        raise HTTPException(status_code=422, detail="Artifact type is required")
    raise HTTPException(status_code=422, detail="Artifact type is unsupported")


@router.post(
    "/review-queue/artifacts/validate",
    response_model=ReviewQueueArtifactIntegrityResult,
)
def validate_review_queue_artifact_integrity(
    payload: dict[str, Any],
    _current_user: User = Depends(get_current_user),
) -> ReviewQueueArtifactIntegrityResult:
    return _validate_supported_artifact(payload)
