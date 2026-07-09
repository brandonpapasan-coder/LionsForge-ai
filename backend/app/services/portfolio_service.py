from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.portfolio import Portfolio, PortfolioHolding, PortfolioTransaction
from app.schemas.portfolio import HoldingCreate, PortfolioCreate, PortfolioTransactionCreate


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
        .options(selectinload(Portfolio.holdings), selectinload(Portfolio.transactions))
        .order_by(Portfolio.created_at.desc())
    )
    return list(db.scalars(statement))


def get_portfolio(db: Session, owner_id: int, portfolio_id: int) -> Portfolio | None:
    statement = (
        select(Portfolio)
        .where(Portfolio.owner_id == owner_id, Portfolio.id == portfolio_id)
        .options(selectinload(Portfolio.holdings), selectinload(Portfolio.transactions))
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


def list_transactions(db: Session, portfolio: Portfolio) -> list[PortfolioTransaction]:
    statement = (
        select(PortfolioTransaction)
        .where(PortfolioTransaction.portfolio_id == portfolio.id)
        .order_by(PortfolioTransaction.created_at.desc())
    )
    return list(db.scalars(statement))


def record_transaction(db: Session, portfolio: Portfolio, payload: PortfolioTransactionCreate) -> PortfolioTransaction:
    tx_type = payload.transaction_type.lower()
    symbol = payload.symbol.strip().upper() if payload.symbol else None
    quantity = payload.quantity
    price = payload.price
    cash_amount = payload.cash_amount

    if tx_type in {"buy", "sell"}:
        if not symbol or quantity <= 0 or price <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Buy and sell transactions require symbol, quantity, and price.",
            )
        cash_amount = quantity * price
        _apply_position_transaction(db, portfolio=portfolio, tx_type=tx_type, symbol=symbol, quantity=quantity, price=price)
    elif tx_type in {"deposit", "withdrawal"}:
        if cash_amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cash transactions require a positive cash_amount.",
            )
    else:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported transaction type.")

    transaction = PortfolioTransaction(
        portfolio_id=portfolio.id,
        transaction_type=tx_type,
        symbol=symbol,
        quantity=quantity,
        price=price,
        cash_amount=cash_amount,
        note=payload.note,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def _find_holding(portfolio: Portfolio, symbol: str) -> PortfolioHolding | None:
    return next((holding for holding in portfolio.holdings if holding.symbol == symbol), None)


def _apply_position_transaction(
    db: Session,
    portfolio: Portfolio,
    tx_type: str,
    symbol: str,
    quantity: Decimal,
    price: Decimal,
) -> None:
    holding = _find_holding(portfolio, symbol)
    if tx_type == "buy":
        if holding is None:
            db.add(PortfolioHolding(portfolio_id=portfolio.id, symbol=symbol, quantity=quantity, average_cost=price))
            return
        current_cost = (holding.average_cost or Decimal("0")) * holding.quantity
        additional_cost = quantity * price
        new_quantity = holding.quantity + quantity
        holding.quantity = new_quantity
        holding.average_cost = (current_cost + additional_cost) / new_quantity if new_quantity > 0 else Decimal("0")
        return

    if holding is None or holding.quantity < quantity:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Sell quantity exceeds current holding.")
    holding.quantity -= quantity
    if holding.quantity == 0:
        db.delete(holding)
