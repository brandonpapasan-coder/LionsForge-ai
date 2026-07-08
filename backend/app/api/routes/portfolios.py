from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.holding_value import HoldingValue
from app.schemas.portfolio import HoldingCreate, HoldingRead, PortfolioCreate, PortfolioRead
from app.schemas.portfolio_value import PortfolioValue
from app.services.portfolio_analytics_service import (
    calculate_holding_cost_basis,
    calculate_holding_gain_loss,
    calculate_holding_market_value,
    calculate_total_market_value,
)
from app.services.portfolio_service import add_holding, create_portfolio, get_portfolio, list_portfolios

router = APIRouter()


@router.post("", response_model=PortfolioRead, status_code=status.HTTP_201_CREATED)
def create_portfolio_endpoint(
    payload: PortfolioCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PortfolioRead:
    return create_portfolio(db, owner_id=current_user.id, payload=payload)


@router.get("", response_model=list[PortfolioRead])
def list_portfolios_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PortfolioRead]:
    return list_portfolios(db, owner_id=current_user.id)


@router.get("/{portfolio_id}/value", response_model=PortfolioValue)
def portfolio_value_endpoint(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PortfolioValue:
    portfolio = get_portfolio(db, owner_id=current_user.id, portfolio_id=portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    return PortfolioValue(
        portfolio_id=portfolio.id,
        name=portfolio.name,
        base_currency=portfolio.base_currency,
        total_market_value=calculate_total_market_value(portfolio),
    )


@router.get("/{portfolio_id}/holdings/value", response_model=list[HoldingValue])
def holding_values_endpoint(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[HoldingValue]:
    portfolio = get_portfolio(db, owner_id=current_user.id, portfolio_id=portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    return [
        HoldingValue(
            symbol=holding.symbol,
            quantity=holding.quantity,
            market_value=calculate_holding_market_value(holding),
            cost_basis=calculate_holding_cost_basis(holding),
            unrealized_gain_loss=calculate_holding_gain_loss(holding),
        )
        for holding in portfolio.holdings
    ]


@router.post("/{portfolio_id}/holdings", response_model=HoldingRead, status_code=status.HTTP_201_CREATED)
def add_holding_endpoint(
    portfolio_id: int,
    payload: HoldingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HoldingRead:
    portfolio = get_portfolio(db, owner_id=current_user.id, portfolio_id=portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    return add_holding(db, portfolio=portfolio, payload=payload)
