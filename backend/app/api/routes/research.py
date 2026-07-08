from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.evidence import EvidenceCollection
from app.schemas.investment_thesis import InvestmentThesis
from app.schemas.research import ResearchInsight, ResearchRequest
from app.schemas.research_confidence import ResearchConfidence
from app.schemas.research_context import ResearchContext
from app.services.evidence_service import collect_symbol_evidence
from app.services.investment_thesis_service import build_investment_thesis
from app.services.research_confidence_service import calculate_research_confidence
from app.services.research_context_service import build_research_context
from app.services.research_service import build_research_insight

router = APIRouter()


@router.post("/analyze", response_model=ResearchInsight)
def analyze_research(request: ResearchRequest) -> ResearchInsight:
    return build_research_insight(request)


@router.get("/context/{ticker}", response_model=ResearchContext)
def research_context(ticker: str, current_user: User = Depends(get_current_user)) -> ResearchContext:
    return build_research_context(ticker)


@router.get("/evidence/{ticker}", response_model=EvidenceCollection)
def research_evidence(ticker: str, current_user: User = Depends(get_current_user)) -> EvidenceCollection:
    return collect_symbol_evidence(ticker)


@router.get("/confidence/{ticker}", response_model=ResearchConfidence)
def research_confidence(ticker: str, current_user: User = Depends(get_current_user)) -> ResearchConfidence:
    return calculate_research_confidence(ticker)


@router.get("/thesis/{ticker}", response_model=InvestmentThesis)
def investment_thesis(ticker: str, current_user: User = Depends(get_current_user)) -> InvestmentThesis:
    return build_investment_thesis(ticker)
