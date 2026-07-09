from app.schemas.research_context import ResearchContext, ResearchNewsContext, ResearchQuoteContext
from app.services.company_news_service import get_company_news
from app.services.market_data_service import get_quote


def build_research_context(ticker: str) -> ResearchContext:
    symbol = ticker.strip().upper()
    quote = get_quote(symbol)
    company_news = get_company_news(symbol)
    news_items = [
        ResearchNewsContext(title=article.title, source=article.source, summary=article.summary)
        for article in company_news.articles
    ]
    return ResearchContext(
        ticker=symbol,
        quote=ResearchQuoteContext(
            symbol=quote.symbol,
            price=quote.price,
            currency=quote.currency,
            source=quote.source,
            is_delayed=quote.is_delayed,
        ),
        news=news_items,
        context_notes=[
            "Quote context is available.",
            "Company news context is available.",
            "Filings and portfolio exposure context are planned next.",
        ],
    )
