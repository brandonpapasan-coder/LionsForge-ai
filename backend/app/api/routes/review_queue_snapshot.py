import hashlib
import json
from collections import Counter
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routes.review_queue import cross_investigation_review_queue
from app.db.session import get_db
from app.models.user import User
from app.schemas.review_queue import ReviewQueueSnapshot, ReviewQueueSnapshotUnsigned

router = APIRouter()


def _canonical_bytes(payload: ReviewQueueSnapshotUnsigned) -> bytes:
    return json.dumps(
        payload.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


@router.get("/review-queue/snapshot")
def export_review_queue_snapshot(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    queue = cross_investigation_review_queue(current_user=current_user, db=db)
    reason_counts = Counter(item.reason_type for item in queue.items)
    unsigned = ReviewQueueSnapshotUnsigned(
        queue=queue,
        reason_counts={key: reason_counts[key] for key in sorted(reason_counts)},
        investigation_count=len({item.investigation_id for item in queue.items}),
    )
    digest = hashlib.sha256(_canonical_bytes(unsigned)).hexdigest()
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
