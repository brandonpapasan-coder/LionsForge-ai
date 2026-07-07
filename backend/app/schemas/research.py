from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=12, examples=["AAPL"])
    include_news: bool = True
    include_risk_summary: bool = True


class ResearchInsight(BaseModel):
    ticker: str
    summary: str
    strengths: list[str]
    risks: list[str]
    next_steps: list[str]
