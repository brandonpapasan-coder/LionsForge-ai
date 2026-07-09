from app.schemas.research import ResearchInsight, ResearchRequest
from app.services.market_data_service import get_quote


def build_research_insight(request: ResearchRequest) -> ResearchInsight:
    ticker = request.ticker.upper()
    quote = get_quote(ticker)
    return ResearchInsight(
        ticker=ticker,
        summary=(
            f"{ticker} research workspace initialized with mock quote context. "
            f"Current placeholder price is {quote.price} {quote.currency} from {quote.source}. "
            "This response uses mock analysis until live market, filings, fundamentals, and news providers are connected."
        ),
        strengths=[
            "Ticker-level research workflow is active.",
            "API contract is ready for AI-generated research summaries.",
            "Market data service boundary is now available for quote enrichment.",
        ],
        risks=[
            "Mock data only; not investment advice.",
            "No live pricing, SEC filings, or broker data connected yet.",
            "Risk scoring model has not been trained or validated.",
        ],
        next_steps=[
            "Connect a live market data provider.",
            "Add news and filings ingestion.",
            "Add user watchlists and portfolio context.",
        ],
    )
