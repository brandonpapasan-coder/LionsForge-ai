from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.market_simulator import SimulatedTrade, SimulationAccount, VirtualPosition
from app.models.user import User
from app.schemas.market_simulator import (
    PortfolioStressCreate,
    PortfolioStressRead,
    ScenarioPointRead,
    ScenarioRunCreate,
    ScenarioRunRead,
    SimulatedTradeCreate,
    SimulatedTradeRead,
    SimulationAccountCreate,
    SimulationAccountRead,
    SimulationPortfolioRead,
    StressedPositionRead,
    VirtualPositionRead,
)
from app.services.market_scenario import run_scenario

router = APIRouter()
MONEY = Decimal("0.01")
QUANTITY = Decimal("0.000001")
RATE = Decimal("0.0001")


def _owned_account(db: Session, owner_id: int, account_id: int) -> SimulationAccount:
    account = db.scalar(
        select(SimulationAccount).where(
            SimulationAccount.id == account_id,
            SimulationAccount.owner_id == owner_id,
        )
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Simulation account not found")
    return account


@router.post("/accounts", response_model=SimulationAccountRead, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: SimulationAccountCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SimulationAccount:
    starting_cash = payload.starting_cash.quantize(MONEY, rounding=ROUND_HALF_UP)
    account = SimulationAccount(
        owner_id=current_user.id,
        name=payload.name,
        starting_cash=starting_cash,
        cash_balance=starting_cash,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/accounts/{account_id}", response_model=SimulationAccountRead)
def get_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SimulationAccount:
    return _owned_account(db, current_user.id, account_id)


@router.post("/trades", response_model=SimulatedTradeRead, status_code=status.HTTP_201_CREATED)
def execute_trade(
    payload: SimulatedTradeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SimulatedTrade:
    account = _owned_account(db, current_user.id, payload.account_id)
    if account.status != "active":
        raise HTTPException(status_code=409, detail="Simulation account is not active")

    quantity = payload.quantity.quantize(QUANTITY, rounding=ROUND_HALF_UP)
    price = payload.execution_price.quantize(QUANTITY, rounding=ROUND_HALF_UP)
    notional = (quantity * price).quantize(MONEY, rounding=ROUND_HALF_UP)
    position = db.scalar(
        select(VirtualPosition).where(
            VirtualPosition.account_id == account.id,
            VirtualPosition.symbol == payload.symbol,
        )
    )

    if payload.side == "buy":
        if Decimal(account.cash_balance) < notional:
            raise HTTPException(status_code=422, detail="Insufficient virtual cash")
        account.cash_balance = Decimal(account.cash_balance) - notional
        if position is None:
            position = VirtualPosition(
                account_id=account.id,
                symbol=payload.symbol,
                quantity=quantity,
                average_price=price,
                last_price=price,
            )
            db.add(position)
        else:
            old_quantity = Decimal(position.quantity)
            new_quantity = old_quantity + quantity
            weighted_cost = old_quantity * Decimal(position.average_price) + quantity * price
            position.quantity = new_quantity
            position.average_price = (weighted_cost / new_quantity).quantize(QUANTITY, rounding=ROUND_HALF_UP)
            position.last_price = price
    else:
        if position is None or Decimal(position.quantity) < quantity:
            raise HTTPException(status_code=422, detail="Insufficient virtual position")
        position.quantity = Decimal(position.quantity) - quantity
        position.last_price = price
        account.cash_balance = Decimal(account.cash_balance) + notional
        if Decimal(position.quantity) == 0:
            db.delete(position)

    trade = SimulatedTrade(
        account_id=account.id,
        symbol=payload.symbol,
        side=payload.side,
        quantity=quantity,
        execution_price=price,
        notional=notional,
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade


@router.get("/portfolio/{account_id}", response_model=SimulationPortfolioRead)
def get_portfolio(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SimulationPortfolioRead:
    account = _owned_account(db, current_user.id, account_id)
    positions = list(
        db.scalars(
            select(VirtualPosition)
            .where(VirtualPosition.account_id == account.id)
            .order_by(VirtualPosition.symbol.asc())
        ).all()
    )
    position_reads: list[VirtualPositionRead] = []
    positions_value = Decimal("0")
    largest_position = Decimal("0")
    for position in positions:
        quantity = Decimal(position.quantity)
        last_price = Decimal(position.last_price)
        average_price = Decimal(position.average_price)
        market_value = (quantity * last_price).quantize(MONEY, rounding=ROUND_HALF_UP)
        unrealized_pnl = (quantity * (last_price - average_price)).quantize(MONEY, rounding=ROUND_HALF_UP)
        positions_value += market_value
        largest_position = max(largest_position, market_value)
        position_reads.append(
            VirtualPositionRead(
                symbol=position.symbol,
                quantity=quantity,
                average_price=average_price,
                last_price=last_price,
                market_value=market_value,
                unrealized_pnl=unrealized_pnl,
            )
        )

    positions_value = positions_value.quantize(MONEY, rounding=ROUND_HALF_UP)
    total_equity = (Decimal(account.cash_balance) + positions_value).quantize(MONEY, rounding=ROUND_HALF_UP)
    total_return = (
        ((total_equity - Decimal(account.starting_cash)) / Decimal(account.starting_cash))
        if Decimal(account.starting_cash)
        else Decimal("0")
    ).quantize(RATE, rounding=ROUND_HALF_UP)
    concentration_risk = (
        largest_position / total_equity if total_equity > 0 else Decimal("0")
    ).quantize(RATE, rounding=ROUND_HALF_UP)

    return SimulationPortfolioRead(
        account=account,
        positions=position_reads,
        positions_value=positions_value,
        total_equity=total_equity,
        total_return=total_return,
        concentration_risk=concentration_risk,
    )


@router.post("/scenarios/run", response_model=ScenarioRunRead)
def execute_scenario(
    payload: ScenarioRunCreate,
    current_user: User = Depends(get_current_user),
) -> ScenarioRunRead:
    del current_user
    points = run_scenario(
        scenario_name=payload.scenario_name,
        initial_price=payload.initial_price,
        steps=payload.steps,
        seed=payload.seed,
    )
    final_price = points[-1].price
    cumulative_return = ((final_price - payload.initial_price) / payload.initial_price).quantize(
        RATE, rounding=ROUND_HALF_UP
    )
    return ScenarioRunRead(
        scenario_name=payload.scenario_name,
        initial_price=payload.initial_price,
        final_price=final_price,
        cumulative_return=cumulative_return,
        steps=payload.steps,
        seed=payload.seed,
        points=[ScenarioPointRead(**point.__dict__) for point in points],
    )


@router.post("/portfolio/{account_id}/stress", response_model=PortfolioStressRead)
def stress_portfolio(
    account_id: int,
    payload: PortfolioStressCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PortfolioStressRead:
    account = _owned_account(db, current_user.id, account_id)
    positions = list(
        db.scalars(
            select(VirtualPosition)
            .where(VirtualPosition.account_id == account.id)
            .order_by(VirtualPosition.symbol.asc())
        ).all()
    )

    starting_positions_value = Decimal("0")
    ending_positions_value = Decimal("0")
    stressed_positions: list[StressedPositionRead] = []
    for position in positions:
        quantity = Decimal(position.quantity)
        starting_price = Decimal(position.last_price)
        scenario_points = run_scenario(
            scenario_name=payload.scenario_name,
            initial_price=starting_price,
            steps=payload.steps,
            seed=payload.seed,
        )
        ending_price = scenario_points[-1].price
        starting_value = (quantity * starting_price).quantize(MONEY, rounding=ROUND_HALF_UP)
        ending_value = (quantity * ending_price).quantize(MONEY, rounding=ROUND_HALF_UP)
        value_change = (ending_value - starting_value).quantize(MONEY, rounding=ROUND_HALF_UP)
        starting_positions_value += starting_value
        ending_positions_value += ending_value
        stressed_positions.append(
            StressedPositionRead(
                symbol=position.symbol,
                starting_price=starting_price,
                ending_price=ending_price,
                quantity=quantity,
                starting_value=starting_value,
                ending_value=ending_value,
                value_change=value_change,
            )
        )

    starting_equity = (Decimal(account.cash_balance) + starting_positions_value).quantize(
        MONEY, rounding=ROUND_HALF_UP
    )
    ending_equity = (Decimal(account.cash_balance) + ending_positions_value).quantize(
        MONEY, rounding=ROUND_HALF_UP
    )
    equity_change = (ending_equity - starting_equity).quantize(MONEY, rounding=ROUND_HALF_UP)
    projected_return = (
        equity_change / starting_equity if starting_equity > 0 else Decimal("0")
    ).quantize(RATE, rounding=ROUND_HALF_UP)

    return PortfolioStressRead(
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
