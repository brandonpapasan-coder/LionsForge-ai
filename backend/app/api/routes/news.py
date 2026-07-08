from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.company_news import CompanyNewsResponse
from app.services.company_news_service import get_company_news

router = APIRouter()


@router.get("/market")
def market_news():
    return {
        "status": "mock",
        "message": "Market news endpoint initialized. Connect a news provider to return live articles and business deal coverage.",
        "articles": [],
        "planned_sources": ["company news", "SEC filings", "press releases", "documented business deals"],
    }


@router.get("/company/{symbol}", response_model=CompanyNewsResponse)
def company_news(symbol: str, current_user: User = Depends(get_current_user)) -> CompanyNewsResponse:
    return get_company_news(symbol)
