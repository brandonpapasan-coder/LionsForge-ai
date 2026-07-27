from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401 - register all mapped tables
from app.db.session import Base
from app.models.promotion import (
    FoundingSubscriberSequence,
    PromotionAuditRecord,
    PromotionCampaign,
    PromotionEligibility,
)
from app.services.promotion_entitlements import (
    PromotionUnavailableError,
    release_abandoned_reservations,
    reserve_founding_position,
)


def _database(tmp_path: Path):
    database_path = tmp_path / "promotion-contention.db"
    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)


def _create_campaign(session_factory, *, capacity: int) -> int:
    with session_factory() as db:
        campaign = PromotionCampaign(
            slug=f"founding-capacity-{capacity}",
            promotion_type="founding",
            discount_percent=50,
            duration_months=12,
            capacity=capacity,
            active=True,
        )
        db.add(campaign)
        db.commit()
        return campaign.id


def test_abandoned_checkout_releases_and_reuses_same_position(tmp_path: Path) -> None:
    engine, session_factory = _database(tmp_path)
    campaign_id = _create_campaign(session_factory, capacity=1)
    reserved_at = datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc).replace(tzinfo=None)

    with session_factory() as db:
        campaign = db.get(PromotionCampaign, campaign_id)
        first_eligibility, first_sequence = reserve_founding_position(
            db,
            campaign=campaign,
            user_id=101,
            verified_account_id="acct-first",
            now=reserved_at,
        )
        first_position = first_sequence.position
        first_eligibility.reserved_until = reserved_at - timedelta(seconds=1)
        db.commit()

    with session_factory() as db:
        assert release_abandoned_reservations(db, now=reserved_at) == 1
        db.commit()

    with session_factory() as db:
        campaign = db.get(PromotionCampaign, campaign_id)
        second_eligibility, second_sequence = reserve_founding_position(
            db,
            campaign=campaign,
            user_id=102,
            verified_account_id="acct-second",
            now=reserved_at,
        )
        db.commit()

        assert first_position == 1
        assert second_sequence.position == 1
        assert second_sequence.eligibility_id == second_eligibility.id
        assert second_sequence.allocation_status == "reserved"
        assert db.scalar(select(PromotionAuditRecord).where(
            PromotionAuditRecord.event_type == "checkout_reservation_expired"
        )) is not None

    engine.dispose()


def test_consumed_position_is_never_reissued(tmp_path: Path) -> None:
    engine, session_factory = _database(tmp_path)
    campaign_id = _create_campaign(session_factory, capacity=1)
    now = datetime(2026, 7, 27, 12, 0)

    with session_factory() as db:
        campaign = db.get(PromotionCampaign, campaign_id)
        eligibility, sequence = reserve_founding_position(
            db,
            campaign=campaign,
            user_id=201,
            verified_account_id="acct-consumed",
            now=now,
        )
        eligibility.status = "active"
        eligibility.reserved_until = None
        sequence.allocation_status = "consumed"
        db.commit()

    with session_factory() as db:
        campaign = db.get(PromotionCampaign, campaign_id)
        with pytest.raises(PromotionUnavailableError, match="allocation is exhausted"):
            reserve_founding_position(
                db,
                campaign=campaign,
                user_id=202,
                verified_account_id="acct-too-late",
                now=now,
            )

        positions = db.scalars(select(FoundingSubscriberSequence.position)).all()
        assert positions == [1]

    engine.dispose()


def test_simultaneous_checkout_cannot_oversubscribe_capacity(tmp_path: Path) -> None:
    engine, session_factory = _database(tmp_path)
    campaign_id = _create_campaign(session_factory, capacity=2)
    now = datetime(2026, 7, 27, 12, 0)

    def attempt(user_id: int) -> str:
        with session_factory() as db:
            campaign = db.get(PromotionCampaign, campaign_id)
            try:
                reserve_founding_position(
                    db,
                    campaign=campaign,
                    user_id=user_id,
                    verified_account_id=f"acct-{user_id}",
                    now=now,
                )
                db.commit()
                return "qualified"
            except PromotionUnavailableError:
                db.rollback()
                return "regular_price"

    with ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(attempt, range(300, 306)))

    with session_factory() as db:
        active_allocations = db.scalars(
            select(FoundingSubscriberSequence).where(
                FoundingSubscriberSequence.allocation_status == "reserved"
            )
        ).all()
        positions = sorted(sequence.position for sequence in active_allocations)

    assert results.count("qualified") == 2
    assert results.count("regular_price") == 4
    assert positions == [1, 2]

    engine.dispose()
