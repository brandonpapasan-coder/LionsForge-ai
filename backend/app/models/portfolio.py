from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from app.db.session import Base


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    owner = relationship(
        "User",
        backref=backref("portfolios", cascade="all, delete-orphan"),
    )
    holdings = relationship("PortfolioHolding", back_populates="portfolio", cascade="all, delete-orphan")
    transactions = relationship("PortfolioTransaction", back_populates="portfolio", cascade="all, delete-orphan")


class PortfolioHolding(Base):
    __tablename__ = "portfolio_holdings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), index=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(12), index=True, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    average_cost: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    portfolio = relationship("Portfolio", back_populates="holdings")


class PortfolioTransaction(Base):
    __tablename__ = "portfolio_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), index=True, nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(16), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(12), index=True, nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0"), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0"), nullable=False)
    cash_amount: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("0"), nullable=False)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    portfolio = relationship("Portfolio", back_populates="transactions")
