from abc import ABC, abstractmethod
from datetime import datetime, timezone

from app.schemas.company_news import CompanyNewsArticle


class NewsProvider(ABC):
    name: str

    @abstractmethod
    def get_company_news(self, symbol: str) -> list[CompanyNewsArticle]:
        raise NotImplementedError


class LiveNewsProvider(NewsProvider):
    def __init__(self, name: str, api_key: str | None = None) -> None:
        self.name = name
        self.api_key = api_key

    def get_company_news(self, symbol: str) -> list[CompanyNewsArticle]:
        raise NotImplementedError(f"Live news provider '{self.name}' is not implemented yet")


class MockNewsProvider(NewsProvider):
    name = "mock-news"

    def get_company_news(self, symbol: str) -> list[CompanyNewsArticle]:
        normalized = symbol.strip().upper()
        return [
            CompanyNewsArticle(
                symbol=normalized,
                title=f"{normalized} research news placeholder",
                source=self.name,
                published_at=datetime.now(timezone.utc),
                summary="Mock company news is available until live news providers are connected.",
            )
        ]
