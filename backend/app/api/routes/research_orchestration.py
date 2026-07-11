from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.research_orchestration import (
    ResearchOrchestrationRequest,
    ResearchOrchestrationResponse,
)
from app.services.research_orchestration import ResearchOrchestrator

router = APIRouter()
orchestrator = ResearchOrchestrator()


@router.post("/run", response_model=ResearchOrchestrationResponse)
def run_research_orchestration(
    payload: ResearchOrchestrationRequest,
    current_user: User = Depends(get_current_user),
) -> ResearchOrchestrationResponse:
    return orchestrator.run(payload, current_user.id)
