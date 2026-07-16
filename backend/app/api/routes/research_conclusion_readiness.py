from collections import Counter
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.evidence import EvidenceRecord, ResearchReviewAction
from app.models.research_project import ResearchProject
from app.models.user import User
from app.schemas.research_conclusion_readiness import ReadinessCheck, ResearchConclusionReadiness

router = APIRouter()
DISCLAIMER = (
    "Readiness describes workflow completeness and provenance risk only. "
    "It does not certify that any claim or conclusion is true, accurate, complete, or predictively valid."
)
ACTIVE_STATUSES = {"open", "acknowledged", "in_progress", "blocked", "deferred"}


def _check(code: str, level: str, passed: bool, message: str, **refs) -> ReadinessCheck:
    return ReadinessCheck(code=code, level=level, passed=passed, message=message, **refs)


@router.get("/projects/{project_id}", response_model=ResearchConclusionReadiness)
def get_conclusion_readiness(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchConclusionReadiness:
    project = db.scalar(
        select(ResearchProject).where(
            ResearchProject.id == project_id,
            ResearchProject.owner_id == current_user.id,
        )
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Research project not found")

    evidence = list(
        db.scalars(
            select(EvidenceRecord).where(
                EvidenceRecord.owner_id == current_user.id,
                EvidenceRecord.project_id == project_id,
            ).order_by(EvidenceRecord.id)
        ).all()
    )
    actions = list(
        db.scalars(
            select(ResearchReviewAction).where(
                ResearchReviewAction.owner_id == current_user.id,
                ResearchReviewAction.project_id == project_id,
            ).order_by(ResearchReviewAction.id)
        ).all()
    )
    now = datetime.utcnow()
    active = [item for item in actions if item.status in ACTIVE_STATUSES]
    high_attention = [item for item in active if item.impact_level == "high_attention"]
    review_required = [item for item in active if item.impact_level == "review_required"]
    overdue = [item for item in active if item.due_at is not None and item.due_at < now]
    unresolved_status = [item for item in evidence if item.validation_status in {"unverified", "needs_review"}]
    contradiction_counts = Counter(
        item.contradiction_key
        for item in evidence
        if item.contradiction_key and item.validation_status not in {"approved", "rejected"}
    )
    contradiction_keys = sorted(key for key, count in contradiction_counts.items() if count > 1)
    contradictory = [item for item in evidence if item.contradiction_key in contradiction_keys]

    checks = [
        _check("evidence_present", "blocking", bool(evidence), "At least one evidence record is required.", evidence_ids=[item.id for item in evidence]),
        _check("contradictions_resolved", "blocking", not contradictory, "Unresolved contradiction groups must be reviewed.", evidence_ids=[item.id for item in contradictory]),
        _check("high_attention_actions_cleared", "blocking", not high_attention, "High-attention review actions must be resolved or dismissed.", action_ids=[item.id for item in high_attention], event_ids=sorted({event for item in high_attention for event in item.supporting_event_ids}), governing_rules=sorted({item.governing_rule for item in high_attention})),
        _check("overdue_actions_cleared", "blocking", not overdue, "Overdue follow-up actions must be addressed.", action_ids=[item.id for item in overdue]),
        _check("review_required_actions_cleared", "caution", not review_required, "Review-required actions remain open.", action_ids=[item.id for item in review_required], event_ids=sorted({event for item in review_required for event in item.supporting_event_ids}), governing_rules=sorted({item.governing_rule for item in review_required})),
        _check("evidence_reviewed", "caution", not unresolved_status, "Some evidence remains unverified or needs review.", evidence_ids=[item.id for item in unresolved_status]),
    ]
    blocking_count = sum(1 for item in checks if item.level == "blocking" and not item.passed)
    caution_count = sum(1 for item in checks if item.level == "caution" and not item.passed)
    state = "blocked" if blocking_count else ("needs_review" if caution_count else "ready_for_user_conclusion")
    next_steps = [item.message for item in checks if not item.passed]
    if not next_steps:
        next_steps = ["The user may draft a conclusion while retaining the evidence and review trail."]
    return ResearchConclusionReadiness(
        project_id=project_id,
        state=state,
        evidence_count=len(evidence),
        blocking_count=blocking_count,
        caution_count=caution_count,
        checks=checks,
        next_steps=next_steps,
        disclaimer=DISCLAIMER,
    )
