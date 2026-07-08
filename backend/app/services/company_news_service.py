from app.schemas.company_news import CompanyNewsResponse
from app.services.news_provider_selector import get_configured_news_provider


def get_company_news(symbol: str) -> CompanyNewsResponse:
    normalized = symbol.strip().upper()
    provider = get_configured_news_provider()
    return CompanyNewsResponse(symbol=normalized, articles=provider.get_company_news(normalized))
