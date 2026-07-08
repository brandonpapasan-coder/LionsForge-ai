from abc import ABC, abstractmethod
from datetime import datetime, timezone

from app.schemas.company_news import CompanyNewsArticle


class NewsProvider(ABC):
    name: str

    @abstractmethod
    def get_company_news(self, symbol: str) -> list[CompanyNewsArticle]:
        raise NotImplementedError


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
