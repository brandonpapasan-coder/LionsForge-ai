from app.schemas.research_context import ResearchContext, ResearchQuoteContext
from app.services.market_data_service import get_quote


def build_research_context(ticker: str) -> ResearchContext:
    symbol = ticker.strip().upper()
    quote = get_quote(symbol)
    return ResearchContext(
        ticker=symbol,
        quote=ResearchQuoteContext(
            symbol=quote.symbol,
            price=quote.price,
            currency=quote.currency,
            source=quote.source,
            is_delayed=quote.is_delayed,
        ),
        context_notes=[
            "Quote context is available.",
            "News, filings, and portfolio exposure context are planned next.",
        ],
    )
