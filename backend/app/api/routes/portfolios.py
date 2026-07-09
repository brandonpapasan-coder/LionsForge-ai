from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.holding_allocation import HoldingAllocation
from app.schemas.holding_value import HoldingValue
from app.schemas.portfolio import (
    HoldingCreate,
    HoldingRead,
    PortfolioAnalytics,
    PortfolioCreate,
    PortfolioInsight,
    PortfolioInsights,
    PortfolioRead,
    PortfolioTransactionCreate,
    PortfolioTransactionRead,
    WatchlistSyncResult,
)
from app.schemas.portfolio_performance import PortfolioPerformance
from app.schemas.portfolio_value import PortfolioValue
from app.services.portfolio_analytics_service import (
    build_portfolio_analytics,
    calculate_allocation_percent,
    calculate_holding_cost_basis,
    calculate_holding_gain_loss,
    calculate_holding_market_value,
    calculate_total_cost_basis,
    calculate_total_gain_loss,
    calculate_total_market_value,
)
from app.services.portfolio_insights_service import build_portfolio_insights
from app.services.portfolio_service import (
    add_holding,
    create_portfolio,
    get_portfolio,
    list_portfolios,
    list_transactions,
    record_transaction,
)
from app.services.portfolio_watchlist_service import sync_portfolio_to_watchlist

router = APIRouter()


def _owned_portfolio_or_404(db: Session, owner_id: int, portfolio_id: int):
    portfolio = get_portfolio(db, owner_id=owner_id, portfolio_id=portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    return portfolio


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


@router.get("/{portfolio_id}", response_model=PortfolioRead)
def get_portfolio_endpoint(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PortfolioRead:
    return _owned_portfolio_or_404(db, current_user.id, portfolio_id)


@router.get("/{portfolio_id}/value", response_model=PortfolioValue)
def portfolio_value_endpoint(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PortfolioValue:
    portfolio = _owned_portfolio_or_404(db, current_user.id, portfolio_id)
    return PortfolioValue(
        portfolio_id=portfolio.id,
        name=portfolio.name,
        base_currency=portfolio.base_currency,
        total_market_value=calculate_total_market_value(portfolio),
    )


@router.get("/{portfolio_id}/performance", response_model=PortfolioPerformance)
def portfolio_performance_endpoint(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PortfolioPerformance:
    portfolio = _owned_portfolio_or_404(db, current_user.id, portfolio_id)
    return PortfolioPerformance(
        portfolio_id=portfolio.id,
        total_market_value=calculate_total_market_value(portfolio),
        total_cost_basis=calculate_total_cost_basis(portfolio),
        total_unrealized_gain_loss=calculate_total_gain_loss(portfolio),
    )


@router.get("/{portfolio_id}/analytics", response_model=PortfolioAnalytics)
def portfolio_analytics_endpoint(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PortfolioAnalytics:
    portfolio = _owned_portfolio_or_404(db, current_user.id, portfolio_id)
    return build_portfolio_analytics(portfolio)


@router.get("/{portfolio_id}/insights", response_model=PortfolioInsights)
def portfolio_insights_endpoint(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PortfolioInsights:
    portfolio = _owned_portfolio_or_404(db, current_user.id, portfolio_id)
    return build_portfolio_insights(db=db, portfolio=portfolio)


@router.get("/{portfolio_id}/holdings/value", response_model=list[HoldingValue])
def holding_values_endpoint(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[HoldingValue]:
    portfolio = _owned_portfolio_or_404(db, current_user.id, portfolio_id)
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


@router.get("/{portfolio_id}/holdings/allocation", response_model=list[HoldingAllocation])
def holding_allocations_endpoint(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[HoldingAllocation]:
    portfolio = _owned_portfolio_or_404(db, current_user.id, portfolio_id)
    return [
        HoldingAllocation(
            symbol=holding.symbol,
            market_value=calculate_holding_market_value(holding),
            allocation_percent=calculate_allocation_percent(holding, portfolio),
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
    portfolio = _owned_portfolio_or_404(db, current_user.id, portfolio_id)
    return add_holding(db, portfolio=portfolio, payload=payload)


@router.post("/{portfolio_id}/transactions", response_model=PortfolioTransactionRead, status_code=status.HTTP_201_CREATED)
def record_transaction_endpoint(
    portfolio_id: int,
    payload: PortfolioTransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PortfolioTransactionRead:
    portfolio = _owned_portfolio_or_404(db, current_user.id, portfolio_id)
    return record_transaction(db, portfolio=portfolio, payload=payload)


@router.get("/{portfolio_id}/transactions", response_model=list[PortfolioTransactionRead])
def list_transactions_endpoint(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PortfolioTransactionRead]:
    portfolio = _owned_portfolio_or_404(db, current_user.id, portfolio_id)
    return list_transactions(db=db, portfolio=portfolio)


@router.post("/{portfolio_id}/watchlist-sync", response_model=WatchlistSyncResult)
def sync_watchlist_endpoint(
    portfolio_id: int,
    watchlist_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WatchlistSyncResult:
    portfolio = _owned_portfolio_or_404(db, current_user.id, portfolio_id)
    return sync_portfolio_to_watchlist(db=db, owner_id=current_user.id, portfolio=portfolio, watchlist_id=watchlist_id)
