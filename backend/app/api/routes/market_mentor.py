from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.market_simulator import SimulationAccount, VirtualPosition
from app.models.user import User
from app.schemas.market_simulator import (
    MentorFeedbackRead,
    PortfolioMentorFeedbackRead,
    PortfolioStressCreate,
    PortfolioStressRead,
    StressedPositionRead,
)
from app.services.market_mentor import build_mentor_feedback
from app.services.market_scenario import run_scenario

router = APIRouter()
MONEY = Decimal("0.01")
RATE = Decimal("0.0001")


@router.post("/portfolio/{account_id}/mentor-feedback", response_model=PortfolioMentorFeedbackRead)
def mentor_feedback(
    account_id: int,
    payload: PortfolioStressCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PortfolioMentorFeedbackRead:
    account = db.scalar(
        select(SimulationAccount).where(
            SimulationAccount.id == account_id,
            SimulationAccount.owner_id == current_user.id,
        )
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Simulation account not found")

    positions = list(
        db.scalars(
            select(VirtualPosition)
            .where(VirtualPosition.account_id == account.id)
            .order_by(VirtualPosition.symbol.asc())
        ).all()
    )
    starting_positions_value = Decimal("0")
    ending_positions_value = Decimal("0")
    largest_position = Decimal("0")
    stressed_positions: list[StressedPositionRead] = []
    for position in positions:
        quantity = Decimal(position.quantity)
        starting_price = Decimal(position.last_price)
        ending_price = run_scenario(
            scenario_name=payload.scenario_name,
            initial_price=starting_price,
            steps=payload.steps,
            seed=payload.seed,
        )[-1].price
        starting_value = (quantity * starting_price).quantize(MONEY, rounding=ROUND_HALF_UP)
        ending_value = (quantity * ending_price).quantize(MONEY, rounding=ROUND_HALF_UP)
        starting_positions_value += starting_value
        ending_positions_value += ending_value
        largest_position = max(largest_position, starting_value)
        stressed_positions.append(
            StressedPositionRead(
                symbol=position.symbol,
                starting_price=starting_price,
                ending_price=ending_price,
                quantity=quantity,
                starting_value=starting_value,
                ending_value=ending_value,
                value_change=(ending_value - starting_value).quantize(MONEY, rounding=ROUND_HALF_UP),
            )
        )

    cash_balance = Decimal(account.cash_balance)
    starting_equity = (cash_balance + starting_positions_value).quantize(MONEY, rounding=ROUND_HALF_UP)
    ending_equity = (cash_balance + ending_positions_value).quantize(MONEY, rounding=ROUND_HALF_UP)
    equity_change = (ending_equity - starting_equity).quantize(MONEY, rounding=ROUND_HALF_UP)
    projected_return = (
        equity_change / starting_equity if starting_equity > 0 else Decimal("0")
    ).quantize(RATE, rounding=ROUND_HALF_UP)
    cash_ratio = cash_balance / starting_equity if starting_equity > 0 else Decimal("0")
    concentration_ratio = largest_position / starting_equity if starting_equity > 0 else Decimal("0")

    stress = PortfolioStressRead(
        account_id=account.id,
        scenario_name=payload.scenario_name,
        steps=payload.steps,
        seed=payload.seed,
        starting_equity=starting_equity,
        ending_equity=ending_equity,
        equity_change=equity_change,
        projected_return=projected_return,
        positions=stressed_positions,
    )
    feedback = build_mentor_feedback(
        projected_return=projected_return,
        cash_ratio=cash_ratio,
        concentration_ratio=concentration_ratio,
        position_count=len(positions),
        scenario_name=payload.scenario_name,
    )
    return PortfolioMentorFeedbackRead(
        stress=stress,
        feedback=MentorFeedbackRead(**feedback.__dict__),
    )
