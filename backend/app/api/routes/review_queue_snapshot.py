import hashlib
import json
from collections import Counter
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routes.review_queue import cross_investigation_review_queue
from app.db.session import get_db
from app.models.user import User
from app.schemas.review_queue import (
    ReviewQueueComparisonReport,
    ReviewQueueComparisonReportUnsigned,
    ReviewQueueComparisonReportVerification,
    ReviewQueueComparisonVerificationReceipt,
    ReviewQueueComparisonVerificationReceiptUnsigned,
    ReviewQueueComparisonVerificationReceiptValidation,
    ReviewQueueSnapshot,
    ReviewQueueSnapshotComparison,
    ReviewQueueSnapshotUnsigned,
)

router = APIRouter()


def _canonical_bytes(payload: BaseModel) -> bytes:
    return json.dumps(
        payload.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _digest(payload: BaseModel) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _current_unsigned(current_user: User, db: Session) -> ReviewQueueSnapshotUnsigned:
    queue = cross_investigation_review_queue(current_user=current_user, db=db)
    reason_counts = Counter(item.reason_type for item in queue.items)
    return ReviewQueueSnapshotUnsigned(
        queue=queue,
        reason_counts={key: reason_counts[key] for key in sorted(reason_counts)},
        investigation_count=len({item.investigation_id for item in queue.items}),
    )


def _verified_comparison(
    prior: ReviewQueueSnapshot,
    current_user: User,
    db: Session,
) -> ReviewQueueSnapshotComparison:
    prior_unsigned = ReviewQueueSnapshotUnsigned(
        **prior.model_dump(exclude={"generated_at", "content_sha256"})
    )
    verified_prior_digest = _digest(prior_unsigned)
    if verified_prior_digest != prior.content_sha256:
        raise HTTPException(
            status_code=400,
            detail="Snapshot digest does not match its canonical payload",
        )

    current_unsigned = _current_unsigned(current_user, db)
    current_digest = _digest(current_unsigned)
    prior_by_key = {item.item_key: item for item in prior.queue.items}
    current_by_key = {item.item_key: item for item in current_unsigned.queue.items}

    added_keys = sorted(current_by_key.keys() - prior_by_key.keys())
    removed_keys = sorted(prior_by_key.keys() - current_by_key.keys())
    unchanged_keys = sorted(
        key
        for key in current_by_key.keys() & prior_by_key.keys()
        if current_by_key[key].model_dump(mode="json")
        == prior_by_key[key].model_dump(mode="json")
    )
    reason_keys = sorted(set(prior.reason_counts) | set(current_unsigned.reason_counts))

    return ReviewQueueSnapshotComparison(
        prior_content_sha256=prior.content_sha256,
        current_content_sha256=current_digest,
        added_items=[current_by_key[key] for key in added_keys],
        removed_items=[prior_by_key[key] for key in removed_keys],
        unchanged_items=[current_by_key[key] for key in unchanged_keys],
        prior_reason_counts=prior.reason_counts,
        current_reason_counts=current_unsigned.reason_counts,
        reason_count_deltas={
            key: current_unsigned.reason_counts.get(key, 0)
            - prior.reason_counts.get(key, 0)
            for key in reason_keys
        },
        prior_investigation_count=prior.investigation_count,
        current_investigation_count=current_unsigned.investigation_count,
        investigation_count_delta=(
            current_unsigned.investigation_count - prior.investigation_count
        ),
    )


def _verified_report(
    report: ReviewQueueComparisonReport,
) -> ReviewQueueComparisonReportVerification:
    unsigned = ReviewQueueComparisonReportUnsigned(
        **report.model_dump(exclude={"generated_at", "content_sha256"})
    )
    recomputed_digest = _digest(unsigned)
    if recomputed_digest != report.content_sha256:
        raise HTTPException(
            status_code=400,
            detail="Comparison report digest does not match its canonical payload",
        )

    comparison = report.comparison
    return ReviewQueueComparisonReportVerification(
        supplied_content_sha256=report.content_sha256,
        recomputed_content_sha256=recomputed_digest,
        prior_content_sha256=comparison.prior_content_sha256,
        current_content_sha256=comparison.current_content_sha256,
        added_item_count=len(comparison.added_items),
        removed_item_count=len(comparison.removed_items),
        unchanged_item_count=len(comparison.unchanged_items),
        reason_count_deltas={
            key: comparison.reason_count_deltas[key]
            for key in sorted(comparison.reason_count_deltas)
        },
        investigation_count_delta=comparison.investigation_count_delta,
    )


def _validated_receipt(
    receipt: ReviewQueueComparisonVerificationReceipt,
) -> ReviewQueueComparisonVerificationReceiptValidation:
    unsigned = ReviewQueueComparisonVerificationReceiptUnsigned(
        **receipt.model_dump(exclude={"generated_at", "content_sha256"})
    )
    recomputed_digest = _digest(unsigned)
    if recomputed_digest != receipt.content_sha256:
        raise HTTPException(
            status_code=400,
            detail="Verification receipt digest does not match its canonical payload",
        )

    return ReviewQueueComparisonVerificationReceiptValidation(
        supplied_content_sha256=receipt.content_sha256,
        recomputed_content_sha256=recomputed_digest,
        verified_report_content_sha256=receipt.verified_report_content_sha256,
        prior_content_sha256=receipt.prior_content_sha256,
        current_content_sha256=receipt.current_content_sha256,
        added_item_count=receipt.added_item_count,
        removed_item_count=receipt.removed_item_count,
        unchanged_item_count=receipt.unchanged_item_count,
        reason_count_deltas={
            key: receipt.reason_count_deltas[key]
            for key in sorted(receipt.reason_count_deltas)
        },
        investigation_count_delta=receipt.investigation_count_delta,
        verification_contract_version=receipt.verification_contract_version,
        verification_artifact_type=receipt.verification_artifact_type,
    )


@router.get("/review-queue/snapshot")
def export_review_queue_snapshot(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    unsigned = _current_unsigned(current_user, db)
    digest = _digest(unsigned)
    snapshot = ReviewQueueSnapshot(
        **unsigned.model_dump(),
        generated_at=datetime.now(timezone.utc),
        content_sha256=digest,
    )
    body = _canonical_bytes(snapshot)
    return Response(
        content=body,
        media_type="application/json",
        headers={
            "Content-Disposition": (
                'attachment; filename="lionsforge-review-queue-snapshot.json"'
            ),
            "X-Content-SHA256": digest,
        },
    )


@router.post(
    "/review-queue/snapshot/compare",
    response_model=ReviewQueueSnapshotComparison,
)
def compare_review_queue_snapshot(
    prior: ReviewQueueSnapshot,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReviewQueueSnapshotComparison:
    return _verified_comparison(prior=prior, current_user=current_user, db=db)


@router.post("/review-queue/snapshot/compare/report")
def export_review_queue_comparison_report(
    prior: ReviewQueueSnapshot,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    comparison = _verified_comparison(
        prior=prior,
        current_user=current_user,
        db=db,
    )
    unsigned = ReviewQueueComparisonReportUnsigned(comparison=comparison)
    digest = _digest(unsigned)
    report = ReviewQueueComparisonReport(
        **unsigned.model_dump(),
        generated_at=datetime.now(timezone.utc),
        content_sha256=digest,
    )
    return Response(
        content=_canonical_bytes(report),
        media_type="application/json",
        headers={
            "Content-Disposition": (
                'attachment; filename="lionsforge-review-queue-comparison-report.json"'
            ),
            "X-Content-SHA256": digest,
        },
    )


@router.post(
    "/review-queue/snapshot/compare/report/verify",
    response_model=ReviewQueueComparisonReportVerification,
)
def verify_review_queue_comparison_report(
    report: ReviewQueueComparisonReport,
    _current_user: User = Depends(get_current_user),
) -> ReviewQueueComparisonReportVerification:
    return _verified_report(report)


@router.post("/review-queue/snapshot/compare/report/verify/receipt")
def export_review_queue_comparison_verification_receipt(
    report: ReviewQueueComparisonReport,
    _current_user: User = Depends(get_current_user),
) -> Response:
    verification = _verified_report(report)
    unsigned = ReviewQueueComparisonVerificationReceiptUnsigned(
        verified_report_content_sha256=verification.recomputed_content_sha256,
        prior_content_sha256=verification.prior_content_sha256,
        current_content_sha256=verification.current_content_sha256,
        added_item_count=verification.added_item_count,
        removed_item_count=verification.removed_item_count,
        unchanged_item_count=verification.unchanged_item_count,
        reason_count_deltas=verification.reason_count_deltas,
        investigation_count_delta=verification.investigation_count_delta,
    )
    digest = _digest(unsigned)
    receipt = ReviewQueueComparisonVerificationReceipt(
        **unsigned.model_dump(),
        generated_at=datetime.now(timezone.utc),
        content_sha256=digest,
    )
    return Response(
        content=_canonical_bytes(receipt),
        media_type="application/json",
        headers={
            "Content-Disposition": (
                'attachment; filename="lionsforge-comparison-verification-receipt.json"'
            ),
            "X-Content-SHA256": digest,
        },
    )


@router.post(
    "/review-queue/snapshot/compare/report/verify/receipt/validate",
    response_model=ReviewQueueComparisonVerificationReceiptValidation,
)
def validate_review_queue_comparison_verification_receipt(
    receipt: ReviewQueueComparisonVerificationReceipt,
    _current_user: User = Depends(get_current_user),
) -> ReviewQueueComparisonVerificationReceiptValidation:
    return _validated_receipt(receipt)
