from datetime import datetime

from pydantic import BaseModel


class CompanyNewsArticle(BaseModel):
    symbol: str
    title: str
    source: str
    published_at: datetime
    url: str | None = None
    summary: str | None = None


class CompanyNewsResponse(BaseModel):
    symbol: str
    articles: list[CompanyNewsArticle]
