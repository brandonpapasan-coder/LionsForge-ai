from datetime import datetime, timezone

from app.schemas.company_news import CompanyNewsArticle, CompanyNewsResponse


def get_company_news(symbol: str) -> CompanyNewsResponse:
    normalized = symbol.strip().upper()
    return CompanyNewsResponse(
        symbol=normalized,
        articles=[
            CompanyNewsArticle(
                symbol=normalized,
                title=f"{normalized} research news placeholder",
                source="mock-news",
                published_at=datetime.now(timezone.utc),
                summary="Mock company news is available until live news providers are connected.",
            )
        ],
    )
