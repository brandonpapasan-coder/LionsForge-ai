from decimal import Decimal

from app.schemas.evidence import EvidenceCollection, EvidenceItem
from app.services.company_news_service import get_company_news
from app.services.market_data_service import get_quote


def collect_symbol_evidence(symbol: str) -> EvidenceCollection:
    normalized = symbol.strip().upper()
    quote = get_quote(normalized)
    news = get_company_news(normalized)
    items: list[EvidenceItem] = [
        EvidenceItem(
            symbol=normalized,
            category="market_quote",
            source=quote.source,
            title=f"{normalized} quote observed",
            observed_at=quote.as_of,
            confidence=Decimal("1.0"),
            summary=f"Latest available quote is {quote.price} {quote.currency}.",
            metadata={"price": str(quote.price), "currency": quote.currency},
        )
    ]
    for article in news.articles:
        items.append(
            EvidenceItem(
                symbol=normalized,
                category="company_news",
                source=article.source,
                title=article.title,
                observed_at=article.published_at,
                confidence=Decimal("0.8"),
                summary=article.summary,
                metadata={"url": article.url},
            )
        )
    return EvidenceCollection(symbol=normalized, items=items)
