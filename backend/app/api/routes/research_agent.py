from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.research_agent import ResearchAgentReport
from app.services.research_agent_service import build_research_agent_report

router = APIRouter()


@router.get("/{symbol}", response_model=ResearchAgentReport)
def research_agent_endpoint(
    symbol: str,
    current_user: User = Depends(get_current_user),
) -> ResearchAgentReport:
    return build_research_agent_report(symbol)
