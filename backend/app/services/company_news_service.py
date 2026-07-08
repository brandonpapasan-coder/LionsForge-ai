from app.schemas.company_news import CompanyNewsResponse
from app.services.news_providers import MockNewsProvider


provider = MockNewsProvider()


def get_company_news(symbol: str) -> CompanyNewsResponse:
    normalized = symbol.strip().upper()
    return CompanyNewsResponse(symbol=normalized, articles=provider.get_company_news(normalized))
