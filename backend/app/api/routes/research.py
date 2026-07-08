from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.research import ResearchInsight, ResearchRequest
from app.schemas.research_context import ResearchContext
from app.services.research_context_service import build_research_context
from app.services.research_service import build_research_insight

router = APIRouter()


@router.post("/analyze", response_model=ResearchInsight)
def analyze_research(request: ResearchRequest) -> ResearchInsight:
    return build_research_insight(request)


@router.get("/context/{ticker}", response_model=ResearchContext)
def research_context(ticker: str, current_user: User = Depends(get_current_user)) -> ResearchContext:
    return build_research_context(ticker)
