from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routes.claim_evidence_validation import validation_map
from app.db.session import get_db
from app.models.user import User
from app.schemas.investigation_report import (
    EvidenceGapRemediationAction,
    EvidenceGapRemediationPlan,
    EvidenceGapSourceRequirement,
    ValidationMapClaim,
)

router = APIRouter()

ActionKey = Literal["contested", "insufficient", "unreviewed", "supported_stale"]
ActionType = Literal[
    "resolve_contradiction",
    "collect_direct_evidence",
    "attach_initial_evidence",
    "refresh_human_review",
]
PlanStatus = Literal["action_required", "complete", "empty"]

_PRIORITY: dict[ActionKey, int] = {
    "contested": 1,
    "insufficient": 2,
    "unreviewed": 3,
    "supported_stale": 4,
}

_PRIORITY_RULES: dict[ActionKey, str] = {
    "contested": (
        "Contested claims are first because recorded contradiction must be resolved "
        "before the claim can be treated as settled."
    ),
    "insufficient": (
        "Insufficient claims follow contested claims because contextual evidence does not "
        "directly test the claim."
    ),
    "unreviewed": (
        "Unreviewed claims follow insufficient claims because no recorded evidence currently "
        "tests the claim."
    ),
    "supported_stale": (
        "Supported claims are included only when their human review is stale and therefore "
        "requires refresh against current evidence."
    ),
}

_SOURCE_CONSTRAINTS = [
    "Use a source with an identifiable title and URL.",
    "Record whether the source supports, contradicts, or only contextualizes the claim.",
    "Do not record source content, credibility, or conclusions that were not actually reviewed.",
]


def _action_key(claim: ValidationMapClaim) -> ActionKey | None:
    if claim.status == "contested":
        return "contested"
    if claim.status == "insufficient":
        return "insufficient"
    if claim.status == "unreviewed":
        return "unreviewed"
    if claim.status == "supported" and claim.human_review.status == "stale":
        return "supported_stale"
    return None


def _action_type(key: ActionKey) -> ActionType:
    values: dict[ActionKey, ActionType] = {
        "contested": "resolve_contradiction",
        "insufficient": "collect_direct_evidence",
        "unreviewed": "attach_initial_evidence",
        "supported_stale": "refresh_human_review",
    }
    return values[key]


def _rationale(key: ActionKey) -> str:
    return {
        "contested": (
            "The claim has recorded contradicting evidence, so the conflicting record must "
            "be reviewed and explicitly resolved or documented."
        ),
        "insufficient": (
            "The claim has only contextual evidence and needs evidence that directly supports "
            "or contradicts it."
        ),
        "unreviewed": (
            "The claim has no attached evidence and cannot yet be tested from recorded sources."
        ),
        "supported_stale": (
            "The evidence currently supports the claim, but the latest human judgment predates "
            "a claim or evidence change."
        ),
    }[key]


def _source_requirements(
    claim: ValidationMapClaim,
    key: ActionKey,
) -> list[EvidenceGapSourceRequirement]:
    if key == "supported_stale":
        return []
    recorded = claim.missing_evidence_requirements or claim.unresolved_gaps
    return [
        EvidenceGapSourceRequirement(
            requirement=requirement,
            source_constraints=list(_SOURCE_CONSTRAINTS),
        )
        for requirement in recorded
        if "human validation judgment" not in requirement.lower()
    ]


def _completion_criteria(claim: ValidationMapClaim, key: ActionKey) -> list[str]:
    criteria = {
        "contested": [
            "Review every currently recorded contradicting evidence item.",
            "Record direct evidence or a claim revision that addresses the contradiction.",
            "Record a current human validation judgment that states any remaining unresolved question.",
        ],
        "insufficient": [
            "Attach at least one evidence item with a direct supporting or contradicting relationship.",
            "Record a current human validation judgment after reviewing the direct evidence.",
        ],
        "unreviewed": [
            "Attach at least one source-backed evidence item that directly tests the claim.",
            "Record the evidence relationship and a current human validation judgment.",
        ],
        "supported_stale": [
            "Review the current claim and all currently recorded evidence.",
            "Record a new human validation judgment without editing the historical judgment.",
        ],
    }[key]
    if claim.human_review.unresolved_questions:
        criteria.append(
            "Address or explicitly preserve the recorded unresolved question in the next human judgment."
        )
    return criteria


def _stored_inputs(claim: ValidationMapClaim) -> list[str]:
    inputs = [
        f"claim_status={claim.status}",
        f"human_review_status={claim.human_review.status}",
        f"supporting_count={claim.relationship_counts['supporting']}",
        f"contradicting_count={claim.relationship_counts['contradicting']}",
        f"contextual_count={claim.relationship_counts['contextual']}",
    ]
    inputs.extend(f"recorded_gap={gap}" for gap in claim.unresolved_gaps)
    return inputs


@router.get(
    "/{investigation_id}/remediation-plan",
    response_model=EvidenceGapRemediationPlan,
)
def remediation_plan(
    investigation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EvidenceGapRemediationPlan:
    mapped = validation_map(
        investigation_id=investigation_id,
        current_user=current_user,
        db=db,
    )
    actions: list[EvidenceGapRemediationAction] = []

    for claim in mapped.claims:
        key = _action_key(claim)
        if key is None:
            continue
        actions.append(
            EvidenceGapRemediationAction(
                claim_id=claim.claim_id,
                claim_sequence=claim.sequence,
                statement=claim.statement,
                claim_status=claim.status,
                priority=_PRIORITY[key],
                priority_rule=_PRIORITY_RULES[key],
                action_type=_action_type(key),
                rationale=_rationale(key),
                source_requirements=_source_requirements(claim, key),
                review_refresh_required=claim.human_review.status == "stale",
                completion_criteria=_completion_criteria(claim, key),
                stored_inputs=_stored_inputs(claim),
            )
        )

    actions.sort(key=lambda item: (item.priority, item.claim_sequence, item.claim_id))
    counts: dict[ActionType, int] = {
        "resolve_contradiction": 0,
        "collect_direct_evidence": 0,
        "attach_initial_evidence": 0,
        "refresh_human_review": 0,
    }
    for action in actions:
        counts[action.action_type] += 1

    status: PlanStatus
    if mapped.status == "empty":
        status = "empty"
    elif actions:
        status = "action_required"
    else:
        status = "complete"

    return EvidenceGapRemediationPlan(
        investigation_id=mapped.investigation_id,
        title=mapped.title,
        status=status,
        actions=actions,
        action_counts=counts,
        generated_from_stored_state_at=mapped.generated_from_stored_state_at,
    )
