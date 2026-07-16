import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.evidence import (
    ResearchGovernanceDigestPreference,
    ResearchGovernanceDigestSnapshot,
    ResearchReviewAction,
    ResearchReviewActionHistory,
)
from app.models.research_project import ResearchProject
from app.models.user import User
from app.schemas.research_governance_digest import (
    ResearchGovernanceDigest,
    ResearchGovernanceDigestHistory,
    ResearchGovernanceDigestItem,
    ResearchGovernanceDigestPreference as DigestPreferenceSchema,
    ResearchGovernanceDigestPreferenceInput,
    ResearchGovernanceDigestSnapshotItem,
    ResearchGovernanceDigestSummary,
)

router = APIRouter()
DISCLAIMER = "Governance digests describe review workflow and provenance risk only. They do not modify evidence, packets, actions, or history and do not certify claim truth, accuracy, professional competence, financial outcomes, or predictive value."
IMPACT_ORDER = ["high_attention", "review_required", "informational"]
CATEGORY_ORDER = ["overdue", "reopened", "newly_opened", "deferred", "recently_resolved"]
OVERDUE_DAYS = {"high_attention": 7, "review_required": 14, "informational": 30}


def _preference_schema(item: ResearchGovernanceDigestPreference) -> DigestPreferenceSchema:
    return DigestPreferenceSchema(
        id=item.id,
        project_ids=sorted(item.project_ids),
        impact_levels=[level for level in IMPACT_ORDER if level in item.impact_levels],
        window_days=item.window_days,
        cadence=item.cadence,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _owned_project_ids(db: Session, owner_id: int, requested: list[int]) -> list[int]:
    query = select(ResearchProject.id).where(ResearchProject.owner_id == owner_id)
    if requested:
        query = query.where(ResearchProject.id.in_(requested))
    project_ids = sorted(db.scalars(query).all())
    if requested and project_ids != sorted(set(requested)):
        raise HTTPException(status_code=404, detail="One or more research projects were not found")
    return project_ids


def _build_digest(
    db: Session,
    owner_id: int,
    project_ids: list[int],
    impact_levels: list[str],
    window_days: int,
    window_end: datetime,
) -> ResearchGovernanceDigest:
    window_start = window_end - timedelta(days=window_days)
    actions = [] if not project_ids else list(
        db.scalars(
            select(ResearchReviewAction)
            .where(
                ResearchReviewAction.owner_id == owner_id,
                ResearchReviewAction.project_id.in_(project_ids),
                ResearchReviewAction.impact_level.in_(impact_levels),
            )
            .order_by(ResearchReviewAction.project_id, ResearchReviewAction.id)
        ).all()
    )
    action_ids = [item.id for item in actions]
    histories = [] if not action_ids else list(
        db.scalars(
            select(ResearchReviewActionHistory)
            .where(
                ResearchReviewActionHistory.owner_id == owner_id,
                ResearchReviewActionHistory.action_id.in_(action_ids),
            )
            .order_by(ResearchReviewActionHistory.created_at, ResearchReviewActionHistory.id)
        ).all()
    )
    history_by_action: dict[int, list[ResearchReviewActionHistory]] = defaultdict(list)
    for history in histories:
        history_by_action[history.action_id].append(history)

    items: list[ResearchGovernanceDigestItem] = []
    counts = Counter()
    impact_rank = {value: index for index, value in enumerate(IMPACT_ORDER)}
    category_rank = {value: index for index, value in enumerate(CATEGORY_ORDER)}

    for action in actions:
        action_history = history_by_action[action.id]
        recent_history = [item for item in action_history if window_start <= item.created_at <= window_end]
        age_days = max(0, (window_end - action.updated_at).days)
        reopen_count = sum(
            1 for item in action_history if item.previous_status == "resolved" and item.new_status == "open"
        )
        categories: list[str] = []
        if action.status != "resolved" and age_days >= OVERDUE_DAYS[action.impact_level]:
            categories.append("overdue")
        if any(item.previous_status == "resolved" and item.new_status == "open" for item in recent_history):
            categories.append("reopened")
        if action.status == "open" and window_start <= action.created_at <= window_end:
            categories.append("newly_opened")
        if action.status == "deferred":
            categories.append("deferred")
        if any(item.new_status == "resolved" for item in recent_history):
            categories.append("recently_resolved")

        for category in categories:
            counts[category] += 1
            items.append(
                ResearchGovernanceDigestItem(
                    category=category,
                    severity_rank=impact_rank[action.impact_level],
                    action_id=action.id,
                    project_id=action.project_id,
                    evidence_id=action.evidence_id,
                    impact_level=action.impact_level,
                    governing_rule=action.governing_rule,
                    status=action.status,
                    reason=action.reason,
                    action_text=action.action_text,
                    supporting_event_ids=sorted(action.supporting_event_ids),
                    age_days=age_days,
                    reopen_count=reopen_count,
                    created_at=action.created_at,
                    updated_at=action.updated_at,
                )
            )

    items.sort(
        key=lambda item: (
            item.severity_rank,
            category_rank[item.category],
            item.project_id,
            item.action_id,
            item.evidence_id,
        )
    )
    summary = ResearchGovernanceDigestSummary(
        newly_opened=counts["newly_opened"],
        overdue=counts["overdue"],
        reopened=counts["reopened"],
        deferred=counts["deferred"],
        recently_resolved=counts["recently_resolved"],
        total_items=len(items),
    )
    canonical = {
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "project_ids": project_ids,
        "impact_levels": impact_levels,
        "summary": summary.model_dump(mode="json"),
        "items": [item.model_dump(mode="json") for item in items],
    }
    content_sha256 = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return ResearchGovernanceDigest(
        generated_at=window_end,
        window_start=window_start,
        window_end=window_end,
        project_ids=project_ids,
        impact_levels=impact_levels,
        summary=summary,
        items=items,
        content_sha256=content_sha256,
        disclaimer=DISCLAIMER,
    )


@router.get("/preferences", response_model=DigestPreferenceSchema | None)
def get_digest_preferences(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> DigestPreferenceSchema | None:
    item = db.scalar(
        select(ResearchGovernanceDigestPreference).where(
            ResearchGovernanceDigestPreference.owner_id == current_user.id
        )
    )
    return None if item is None else _preference_schema(item)


@router.put("/preferences", response_model=DigestPreferenceSchema)
def update_digest_preferences(
    request: ResearchGovernanceDigestPreferenceInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DigestPreferenceSchema:
    project_ids = _owned_project_ids(db, current_user.id, request.project_ids)
    impact_levels = [level for level in IMPACT_ORDER if level in request.impact_levels]
    if not impact_levels:
        raise HTTPException(status_code=400, detail="At least one impact level is required")
    item = db.scalar(
        select(ResearchGovernanceDigestPreference).where(
            ResearchGovernanceDigestPreference.owner_id == current_user.id
        )
    )
    if item is None:
        item = ResearchGovernanceDigestPreference(owner_id=current_user.id)
        db.add(item)
    item.project_ids = project_ids
    item.impact_levels = impact_levels
    item.window_days = request.window_days
    item.cadence = request.cadence
    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return _preference_schema(item)


@router.get("/preview", response_model=ResearchGovernanceDigest)
def preview_digest(
    project_ids: list[int] = Query(default=[]),
    impact_levels: list[str] = Query(default=[]),
    window_days: int | None = Query(default=None, ge=1, le=365),
    as_of: datetime | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchGovernanceDigest:
    preference = db.scalar(
        select(ResearchGovernanceDigestPreference).where(
            ResearchGovernanceDigestPreference.owner_id == current_user.id
        )
    )
    requested_projects = project_ids or (preference.project_ids if preference else [])
    selected_projects = _owned_project_ids(db, current_user.id, requested_projects)
    requested_impacts = impact_levels or (preference.impact_levels if preference else IMPACT_ORDER)
    selected_impacts = [level for level in IMPACT_ORDER if level in requested_impacts]
    if not selected_impacts:
        raise HTTPException(status_code=400, detail="At least one valid impact level is required")
    selected_window = window_days or (preference.window_days if preference else 30)
    return _build_digest(
        db, current_user.id, selected_projects, selected_impacts, selected_window, as_of or datetime.utcnow()
    )


@router.post("/generate", response_model=ResearchGovernanceDigest)
def generate_digest_snapshot(
    as_of: datetime | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchGovernanceDigest:
    preference = db.scalar(
        select(ResearchGovernanceDigestPreference).where(
            ResearchGovernanceDigestPreference.owner_id == current_user.id
        )
    )
    if preference is None:
        raise HTTPException(status_code=409, detail="Digest preferences must be saved before generation")
    projects = _owned_project_ids(db, current_user.id, preference.project_ids)
    impacts = [level for level in IMPACT_ORDER if level in preference.impact_levels]
    digest = _build_digest(
        db, current_user.id, projects, impacts, preference.window_days, as_of or datetime.utcnow()
    )
    db.add(
        ResearchGovernanceDigestSnapshot(
            owner_id=current_user.id,
            preference_id=preference.id,
            generated_at=digest.generated_at,
            window_start=digest.window_start,
            window_end=digest.window_end,
            content_sha256=digest.content_sha256,
            item_count=digest.summary.total_items,
            summary=digest.summary.model_dump(mode="json"),
        )
    )
    db.commit()
    return digest


@router.get("/history", response_model=ResearchGovernanceDigestHistory)
def get_digest_history(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchGovernanceDigestHistory:
    snapshots = list(
        db.scalars(
            select(ResearchGovernanceDigestSnapshot)
            .where(ResearchGovernanceDigestSnapshot.owner_id == current_user.id)
            .order_by(
                ResearchGovernanceDigestSnapshot.generated_at.desc(),
                ResearchGovernanceDigestSnapshot.id.desc(),
            )
            .limit(limit)
        ).all()
    )
    return ResearchGovernanceDigestHistory(
        snapshots=[
            ResearchGovernanceDigestSnapshotItem(
                id=item.id,
                generated_at=item.generated_at,
                window_start=item.window_start,
                window_end=item.window_end,
                content_sha256=item.content_sha256,
                item_count=item.item_count,
                summary=item.summary,
            )
            for item in snapshots
        ]
    )
