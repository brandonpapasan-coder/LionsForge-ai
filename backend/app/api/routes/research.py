from fastapi import APIRouter

from app.schemas.research import ResearchInsight, ResearchRequest
from app.services.research_service import build_research_insight

router = APIRouter()


@router.post("/analyze", response_model=ResearchInsight)
def analyze_research(request: ResearchRequest) -> ResearchInsight:
    return build_research_insight(request)
