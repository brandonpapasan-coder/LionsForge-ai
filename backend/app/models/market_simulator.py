from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class SimulationAccount(Base):
    __tablename__ = "simulation_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), default="Primary Simulator", nullable=False)
    starting_cash: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    cash_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="active", index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class VirtualPosition(Base):
    __tablename__ = "virtual_positions"
    __table_args__ = (UniqueConstraint("account_id", "symbol", name="uq_virtual_position_account_symbol"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("simulation_accounts.id"), index=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    average_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    last_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SimulatedTrade(Base):
    __tablename__ = "simulated_trades"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("simulation_accounts.id"), index=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    execution_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    notional: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class MarketLearningSession(Base):
    __tablename__ = "market_learning_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("simulation_accounts.id"), index=True, nullable=False)
    scenario_name: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    steps: Mapped[int] = mapped_column(nullable=False)
    seed: Mapped[int] = mapped_column(nullable=False)
    risk_tier: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    projected_return: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    learner_reflection: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="completed", index=True, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class MarketLearningEvidenceLink(Base):
    __tablename__ = "market_learning_evidence_links"
    __table_args__ = (
        UniqueConstraint("session_id", name="uq_market_learning_evidence_session"),
        UniqueConstraint("evidence_id", name="uq_market_learning_evidence_record"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("market_learning_sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    evidence_id: Mapped[int] = mapped_column(
        ForeignKey("evidence_records.id", ondelete="CASCADE"), index=True, nullable=False
    )
    project_id: Mapped[int] = mapped_column(
        ForeignKey("research_projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
