import hashlib
import json
from collections import Counter
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routes.review_queue import cross_investigation_review_queue
from app.db.session import get_db
from app.models.user import User
from app.schemas.review_queue import (
    ReviewQueueSnapshot,
    ReviewQueueSnapshotComparison,
    ReviewQueueSnapshotUnsigned,
)

router = APIRouter()


def _canonical_bytes(payload: ReviewQueueSnapshotUnsigned) -> bytes:
    return json.dumps(
        payload.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _digest(payload: ReviewQueueSnapshotUnsigned) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _current_unsigned(current_user: User, db: Session) -> ReviewQueueSnapshotUnsigned:
    queue = cross_investigation_review_queue(current_user=current_user, db=db)
    reason_counts = Counter(item.reason_type for item in queue.items)
    return ReviewQueueSnapshotUnsigned(
        queue=queue,
        reason_counts={key: reason_counts[key] for key in sorted(reason_counts)},
        investigation_count=len({item.investigation_id for item in queue.items}),
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
    body = json.dumps(
        snapshot.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
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


@router.post("/review-queue/snapshot/compare", response_model=ReviewQueueSnapshotComparison)
def compare_review_queue_snapshot(
    prior: ReviewQueueSnapshot,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReviewQueueSnapshotComparison:
    prior_unsigned = ReviewQueueSnapshotUnsigned(**prior.model_dump(exclude={"generated_at", "content_sha256"}))
    verified_prior_digest = _digest(prior_unsigned)
    if verified_prior_digest != prior.content_sha256:
        raise HTTPException(status_code=400, detail="Snapshot digest does not match its canonical payload")

    current_unsigned = _current_unsigned(current_user, db)
    current_digest = _digest(current_unsigned)
    prior_by_key = {item.item_key: item for item in prior.queue.items}
    current_by_key = {item.item_key: item for item in current_unsigned.queue.items}

    added_keys = sorted(current_by_key.keys() - prior_by_key.keys())
    removed_keys = sorted(prior_by_key.keys() - current_by_key.keys())
    unchanged_keys = sorted(
        key for key in current_by_key.keys() & prior_by_key.keys()
        if current_by_key[key].model_dump(mode="json") == prior_by_key[key].model_dump(mode="json")
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
            key: current_unsigned.reason_counts.get(key, 0) - prior.reason_counts.get(key, 0)
            for key in reason_keys
        },
        prior_investigation_count=prior.investigation_count,
        current_investigation_count=current_unsigned.investigation_count,
        investigation_count_delta=(
            current_unsigned.investigation_count - prior.investigation_count
        ),
    )
