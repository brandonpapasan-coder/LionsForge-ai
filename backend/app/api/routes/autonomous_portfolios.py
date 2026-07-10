from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.autonomous_portfolio import AutonomousPortfolioReport
from app.services.autonomous_portfolio_service import build_autonomous_portfolio_report
from app.services.portfolio_service import get_portfolio

router = APIRouter()


@router.get("/{portfolio_id}/intelligence", response_model=AutonomousPortfolioReport)
def autonomous_portfolio_intelligence_endpoint(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AutonomousPortfolioReport:
    portfolio = get_portfolio(db, owner_id=current_user.id, portfolio_id=portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    return build_autonomous_portfolio_report(portfolio)
