from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.evidence import EvidenceCollection
from app.schemas.investment_thesis import InvestmentThesis
from app.schemas.research import ResearchInsight, ResearchRequest
from app.schemas.research_confidence import ResearchConfidence
from app.schemas.research_context import ResearchContext
from app.schemas.research_report import ResearchReport, ResearchReportList, ResearchReportRead, ResearchReportRequest
from app.services.evidence_service import collect_symbol_evidence
from app.services.investment_thesis_service import build_investment_thesis
from app.services.research_confidence_service import calculate_research_confidence
from app.services.research_context_service import build_research_context
from app.services.research_report_service import build_research_report, get_research_report, list_research_reports
from app.services.research_service import build_research_insight

router = APIRouter()


@router.post("/analyze", response_model=ResearchInsight)
def analyze_research(request: ResearchRequest) -> ResearchInsight:
    return build_research_insight(request)


@router.post("/reports", response_model=ResearchReport)
def generate_research_report(
    request: ResearchReportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchReport:
    return build_research_report(
        symbol=request.symbol,
        user=current_user,
        db=db,
        persist=request.persist,
    )


@router.get("/reports", response_model=ResearchReportList)
def list_reports(
    symbol: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchReportList:
    return ResearchReportList(
        symbol=symbol.strip().upper() if symbol else None,
        reports=list_research_reports(db=db, user=current_user, symbol=symbol),
    )


@router.get("/reports/{report_id}", response_model=ResearchReportRead)
def read_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchReportRead:
    report = get_research_report(db=db, user=current_user, report_id=report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research report not found")
    return report


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
