from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.portfolio import HoldingCreate, HoldingRead, PortfolioCreate, PortfolioRead
from app.services.portfolio_service import add_holding, create_portfolio, get_portfolio, list_portfolios

router = APIRouter()


@router.post("", response_model=PortfolioRead, status_code=status.HTTP_201_CREATED)
def create_portfolio_endpoint(
    payload: PortfolioCreate,
    owner_id: int = Query(default=1, ge=1, description="Temporary owner id until auth dependency is added."),
    db: Session = Depends(get_db),
) -> PortfolioRead:
    return create_portfolio(db, owner_id=owner_id, payload=payload)


@router.get("", response_model=list[PortfolioRead])
def list_portfolios_endpoint(
    owner_id: int = Query(default=1, ge=1, description="Temporary owner id until auth dependency is added."),
    db: Session = Depends(get_db),
) -> list[PortfolioRead]:
    return list_portfolios(db, owner_id=owner_id)


@router.post("/{portfolio_id}/holdings", response_model=HoldingRead, status_code=status.HTTP_201_CREATED)
def add_holding_endpoint(
    portfolio_id: int,
    payload: HoldingCreate,
    owner_id: int = Query(default=1, ge=1, description="Temporary owner id until auth dependency is added."),
    db: Session = Depends(get_db),
) -> HoldingRead:
    portfolio = get_portfolio(db, owner_id=owner_id, portfolio_id=portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    return add_holding(db, portfolio=portfolio, payload=payload)
