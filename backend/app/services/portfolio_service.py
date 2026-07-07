from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.portfolio import Portfolio, PortfolioHolding
from app.schemas.portfolio import HoldingCreate, PortfolioCreate


def create_portfolio(db: Session, owner_id: int, payload: PortfolioCreate) -> Portfolio:
    portfolio = Portfolio(
        owner_id=owner_id,
        name=payload.name.strip(),
        base_currency=payload.base_currency.upper(),
    )
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return portfolio


def list_portfolios(db: Session, owner_id: int) -> list[Portfolio]:
    statement = (
        select(Portfolio)
        .where(Portfolio.owner_id == owner_id)
        .options(selectinload(Portfolio.holdings))
        .order_by(Portfolio.created_at.desc())
    )
    return list(db.scalars(statement))


def get_portfolio(db: Session, owner_id: int, portfolio_id: int) -> Portfolio | None:
    statement = (
        select(Portfolio)
        .where(Portfolio.owner_id == owner_id, Portfolio.id == portfolio_id)
        .options(selectinload(Portfolio.holdings))
    )
    return db.scalar(statement)


def add_holding(db: Session, portfolio: Portfolio, payload: HoldingCreate) -> PortfolioHolding:
    holding = PortfolioHolding(
        portfolio_id=portfolio.id,
        symbol=payload.symbol.strip().upper(),
        quantity=payload.quantity,
        average_cost=payload.average_cost,
    )
    db.add(holding)
    db.commit()
    db.refresh(holding)
    return holding
