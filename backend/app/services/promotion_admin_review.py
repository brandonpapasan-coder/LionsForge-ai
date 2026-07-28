from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.promotion import PromotionEligibility
from app.services.promotion_entitlements import append_audit_record


ALLOWED_REVIEW_DECISIONS = {"confirm", "suspend", "revoke", "restore"}


@dataclass(frozen=True)
class AdministrativeReviewResult:
    previous_status: str
    new_status: str
    audit_record_sha256: str


def review_promotion_eligibility(
    db: Session,
    *,
    eligibility: PromotionEligibility,
    decision: str,
    reason_code: str,
    administrator_reference: str,
    reviewed_at: datetime,
    notes: str | None = None,
) -> AdministrativeReviewResult:
    if decision not in ALLOWED_REVIEW_DECISIONS:
        raise ValueError("unsupported administrative promotion review decision")
    if not reason_code or not administrator_reference:
        raise ValueError("administrative review requires actor and reason provenance")

    previous_status = eligibility.status
    status_by_decision = {
        "confirm": previous_status,
        "suspend": "review",
        "revoke": "ineligible",
        "restore": "active",
    }
    new_status = status_by_decision[decision]
    eligibility.status = new_status

    audit = append_audit_record(
        db,
        event_type="administrative_eligibility_review",
        reason_code=reason_code,
        actor_type="administrator",
        actor_reference=administrator_reference,
        occurred_at=reviewed_at,
        payload={
            "decision": decision,
            "previous_status": previous_status,
            "new_status": new_status,
            "notes": notes,
        },
        campaign_id=eligibility.campaign_id,
        eligibility_id=eligibility.id,
    )
    return AdministrativeReviewResult(
        previous_status=previous_status,
        new_status=new_status,
        audit_record_sha256=audit.record_sha256,
    )
