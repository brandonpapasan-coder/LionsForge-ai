from app.schemas.research import ResearchInsight, ResearchRequest


def build_research_insight(request: ResearchRequest) -> ResearchInsight:
    ticker = request.ticker.upper()
    return ResearchInsight(
        ticker=ticker,
        summary=(
            f"{ticker} research workspace initialized. This response uses mock analysis until "
            "live market, filings, fundamentals, and news providers are connected."
        ),
        strengths=[
            "Ticker-level research workflow is active.",
            "API contract is ready for AI-generated research summaries.",
            "Service boundary is prepared for market data and news integrations.",
        ],
        risks=[
            "Mock data only; not investment advice.",
            "No live pricing, SEC filings, or broker data connected yet.",
            "Risk scoring model has not been trained or validated.",
        ],
        next_steps=[
            "Connect a market data provider.",
            "Add news and filings ingestion.",
            "Add user watchlists and portfolio context.",
        ],
    )
