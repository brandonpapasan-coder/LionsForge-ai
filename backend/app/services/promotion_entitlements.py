from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.promotion import (
    FoundingSubscriberSequence,
    PromotionAuditRecord,
    PromotionCampaign,
    PromotionEligibility,
)

FOUNDING_CAPACITY = 20_000
RESERVATION_MINUTES = 30
ACTIVE_ELIGIBILITY_STATUSES = {"reserved", "active", "grace"}
TERMINAL_LIFECYCLE_EVENTS = {"canceled", "chargeback", "lapsed"}


class PromotionUnavailableError(RuntimeError):
    pass


class PromotionConflictError(RuntimeError):
    pass


@dataclass(frozen=True)
class LifecycleDecision:
    eligibility_status: str
    protection_status: str
    release_founding_position: bool
    reason_code: str


def decide_lifecycle_transition(
    *,
    event_type: str,
    promotion_type: str,
    continuous_subscription_required: bool,
    within_payment_grace: bool = False,
) -> LifecycleDecision:
    if event_type == "payment_failed" and within_payment_grace:
        return LifecycleDecision("grace", "grace", False, "payment_failure_grace_started")
    if event_type == "payment_recovered":
        return LifecycleDecision("active", "active", False, "payment_recovered_in_grace")
    if event_type == "refund":
        return LifecycleDecision("review", "suspended", False, "refund_requires_policy_review")
    if event_type in TERMINAL_LIFECYCLE_EVENTS:
        # A position is consumed once a paid founding subscription activates. Later
        # cancellation, lapse, refund, or chargeback never expands the first-20,000 cohort.
        return LifecycleDecision("ended", "ended", False, f"subscription_{event_type}")
    if event_type == "reactivated":
        if continuous_subscription_required:
            return LifecycleDecision("ineligible", "ended", False, "continuous_subscription_broken")
        return LifecycleDecision("active", "active", False, "reactivated_without_continuity_rule")
    raise ValueError(f"unsupported promotion lifecycle event: {event_type}")


def enforce_non_stacking(db: Session, *, user_id: int, exclude_campaign_id: int | None = None) -> None:
    statement = select(PromotionEligibility.id).where(
        PromotionEligibility.user_id == user_id,
        PromotionEligibility.status.in_(ACTIVE_ELIGIBILITY_STATUSES),
    )
    if exclude_campaign_id is not None:
        statement = statement.where(PromotionEligibility.campaign_id != exclude_campaign_id)
    if db.execute(statement.limit(1)).scalar_one_or_none() is not None:
        raise PromotionConflictError("an active promotion entitlement already exists for this account")


def reserve_beta_eligibility(
    db: Session,
    *,
    campaign: PromotionCampaign,
    user_id: int,
    verified_account_id: str,
    now: datetime,
) -> PromotionEligibility:
    if not campaign.active or campaign.promotion_type != "beta":
        raise PromotionUnavailableError("beta campaign is not active")
    enforce_non_stacking(db, user_id=user_id, exclude_campaign_id=campaign.id)
    eligibility = PromotionEligibility(
        campaign_id=campaign.id,
        user_id=user_id,
        status="reserved",
        verified_account_id=verified_account_id,
        reserved_until=now + timedelta(minutes=RESERVATION_MINUTES),
        eligibility_reason="verified_beta_tester",
    )
    db.add(eligibility)
    try:
        db.flush()
    except IntegrityError as exc:
        raise PromotionConflictError("beta eligibility is already reserved for this account") from exc
    return eligibility


def reserve_founding_position(
    db: Session,
    *,
    campaign: PromotionCampaign,
    user_id: int,
    verified_account_id: str,
    now: datetime,
) -> tuple[PromotionEligibility, FoundingSubscriberSequence]:
    if not campaign.active or campaign.promotion_type != "founding":
        raise PromotionUnavailableError("founding campaign is not active")
    enforce_non_stacking(db, user_id=user_id, exclude_campaign_id=campaign.id)

    capacity = min(campaign.capacity or FOUNDING_CAPACITY, FOUNDING_CAPACITY)
    for _ in range(8):
        try:
            with db.begin_nested():
                eligibility = PromotionEligibility(
                    campaign_id=campaign.id,
                    user_id=user_id,
                    status="reserved",
                    verified_account_id=verified_account_id,
                    reserved_until=now + timedelta(minutes=RESERVATION_MINUTES),
                    eligibility_reason="founding_checkout",
                )
                db.add(eligibility)
                db.flush()

                released = db.execute(
                    select(FoundingSubscriberSequence)
                    .where(
                        FoundingSubscriberSequence.campaign_id == campaign.id,
                        FoundingSubscriberSequence.allocation_status == "released",
                    )
                    .order_by(FoundingSubscriberSequence.position)
                    .with_for_update(skip_locked=True)
                    .limit(1)
                ).scalar_one_or_none()
                if released is not None:
                    released.eligibility_id = eligibility.id
                    released.allocation_status = "reserved"
                    released.reserved_at = now
                    released.released_at = None
                    db.flush()
                    return eligibility, released

                highest = db.execute(
                    select(func.max(FoundingSubscriberSequence.position)).where(
                        FoundingSubscriberSequence.campaign_id == campaign.id
                    )
                ).scalar_one()
                position = (highest or 0) + 1
                if position > capacity:
                    raise PromotionUnavailableError("founding subscriber allocation is exhausted")

                sequence = FoundingSubscriberSequence(
                    campaign_id=campaign.id,
                    eligibility_id=eligibility.id,
                    position=position,
                    allocation_status="reserved",
                    reserved_at=now,
                )
                db.add(sequence)
                db.flush()
                return eligibility, sequence
        except IntegrityError:
            # The savepoint rolls back only this allocation attempt. The caller's
            # surrounding transaction remains usable for a bounded retry.
            continue
    raise PromotionConflictError("founding position contention exceeded retry limit")


def release_abandoned_reservations(db: Session, *, now: datetime) -> int:
    expired = db.execute(
        select(PromotionEligibility).where(
            PromotionEligibility.status == "reserved",
            PromotionEligibility.reserved_until.is_not(None),
            PromotionEligibility.reserved_until < now,
        )
    ).scalars().all()
    for eligibility in expired:
        eligibility.status = "expired"
        sequence = db.execute(
            select(FoundingSubscriberSequence).where(
                FoundingSubscriberSequence.eligibility_id == eligibility.id,
                FoundingSubscriberSequence.allocation_status == "reserved",
            )
        ).scalar_one_or_none()
        if sequence is not None:
            sequence.allocation_status = "released"
            sequence.released_at = now
        append_audit_record(
            db,
            campaign_id=eligibility.campaign_id,
            eligibility_id=eligibility.id,
            event_type="checkout_reservation_expired",
            reason_code="abandoned_checkout_released",
            actor_type="system",
            occurred_at=now,
            payload={"founding_position": sequence.position if sequence is not None else None},
        )
    return len(expired)


def append_audit_record(
    db: Session,
    *,
    event_type: str,
    reason_code: str,
    actor_type: str,
    occurred_at: datetime,
    payload: dict[str, Any],
    campaign_id: int | None = None,
    eligibility_id: int | None = None,
    redemption_id: int | None = None,
    actor_reference: str | None = None,
) -> PromotionAuditRecord:
    previous = db.execute(
        select(PromotionAuditRecord.record_sha256)
        .order_by(PromotionAuditRecord.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    canonical = {
        "actor_reference": actor_reference,
        "actor_type": actor_type,
        "campaign_id": campaign_id,
        "eligibility_id": eligibility_id,
        "event_payload": payload,
        "event_type": event_type,
        "occurred_at": occurred_at.isoformat(timespec="microseconds"),
        "previous_record_sha256": previous,
        "reason_code": reason_code,
        "redemption_id": redemption_id,
    }
    digest = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    record = PromotionAuditRecord(
        campaign_id=campaign_id,
        eligibility_id=eligibility_id,
        redemption_id=redemption_id,
        actor_type=actor_type,
        actor_reference=actor_reference,
        event_type=event_type,
        reason_code=reason_code,
        event_payload=payload,
        previous_record_sha256=previous,
        record_sha256=digest,
        occurred_at=occurred_at,
    )
    db.add(record)
    db.flush()
    return record


def payment_provider_metadata(*, eligibility_id: int, campaign_slug: str, entitlement_id: str) -> dict[str, str]:
    return {
        "onyxmane_promotion_eligibility_id": str(eligibility_id),
        "onyxmane_promotion_campaign": campaign_slug,
        "onyxmane_internal_entitlement_id": entitlement_id,
    }
