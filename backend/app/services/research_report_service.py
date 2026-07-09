from datetime import datetime, timezone
from decimal import Decimal
from time import perf_counter
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.research_report import ResearchReport as ResearchReportModel
from app.models.user import User
from app.schemas.evidence import EvidenceItem
from app.schemas.research_report import (
    ResearchReport,
    ResearchReportMetadata,
    ResearchReportRead,
    ResearchReportSection,
)
from app.services.evidence_service import collect_symbol_evidence
from app.services.investment_thesis_service import build_investment_thesis
from app.services.market_data_service import get_historical_prices, get_quote
from app.services.research_confidence_service import calculate_research_confidence
from app.services.research_context_service import build_research_context

TEMPLATE_VERSION = "rc1-research-template-v1"
MODEL_VERSION = "deterministic-research-engine-v1"


def _confidence_level(score: Decimal) -> str:
    if score >= Decimal("0.8"):
        return "high"
    if score >= Decimal("0.55"):
        return "medium"
    return "low"


def _evidence_ids(items: list[EvidenceItem], category: str | None = None) -> list[str]:
    if category is None:
        return [item.evidence_id for item in items]
    return [item.evidence_id for item in items if item.category == category]


def _next_version(db: Session, user_id: int, symbol: str) -> int:
    statement = (
        select(ResearchReportModel)
        .where(ResearchReportModel.user_id == user_id, ResearchReportModel.symbol == symbol)
        .order_by(ResearchReportModel.version.desc())
        .limit(1)
    )
    latest = db.execute(statement).scalars().first()
    return 1 if latest is None else latest.version + 1


def build_research_report(symbol: str, user: User, db: Session, persist: bool = True) -> ResearchReport:
    started_at = perf_counter()
    normalized = symbol.strip().upper()
    quote = get_quote(normalized)
    historical_prices = get_historical_prices(normalized, limit=5)
    context = build_research_context(normalized)
    evidence_collection = collect_symbol_evidence(normalized)
    confidence = calculate_research_confidence(normalized)
    thesis = build_investment_thesis(normalized)
    evidence_items = evidence_collection.items
    confidence_score = confidence.confidence
    level = _confidence_level(confidence_score)
    version = _next_version(db, user.id, normalized)
    generated_at = datetime.now(timezone.utc)
    data_snapshot_id = f"{normalized}:{quote.as_of.isoformat()}:{len(evidence_items)}"

    latest_close = historical_prices[-1].close if historical_prices else quote.price
    earliest_close = historical_prices[0].close if historical_prices else quote.price
    price_change = latest_close - earliest_close

    sections = [
        ResearchReportSection(
            title="Market Snapshot",
            summary=(
                f"{normalized} latest available quote is {quote.price} {quote.currency} "
                f"from {quote.source}. Five-period observed price change is {price_change}."
            ),
            bullets=[
                f"Latest quote: {quote.price} {quote.currency}",
                f"Data source: {quote.source}",
                f"Historical observations reviewed: {len(historical_prices)}",
            ],
            evidence_ids=_evidence_ids(evidence_items, "market_quote"),
        ),
        ResearchReportSection(
            title="Business and News Context",
            summary=(
                f"The research context includes {len(context.news)} recent news item(s) "
                f"and market data for {normalized}."
            ),
            bullets=[item.title for item in context.news[:3]],
            evidence_ids=_evidence_ids(evidence_items, "company_news"),
        ),
        ResearchReportSection(
            title="Investment Thesis",
            summary=thesis.summary,
            bullets=thesis.bull_case[:2] + thesis.bear_case[:2],
            evidence_ids=thesis.supporting_evidence_ids,
        ),
    ]

    data_quality_flags: list[str] = []
    if not historical_prices:
        data_quality_flags.append("historical_prices_missing")
    if len(evidence_items) < 2:
        data_quality_flags.append("limited_evidence")
    if quote.is_delayed:
        data_quality_flags.append("quote_may_be_delayed")

    executive_summary = (
        f"{normalized} research report generated using {len(evidence_items)} evidence item(s). "
        f"Confidence is {level} based on evidence completeness, source confidence, and current market context."
    )

    processing_duration_ms = (perf_counter() - started_at) * 1000
    report = ResearchReport(
        metadata=ResearchReportMetadata(
            report_id=str(uuid4()),
            symbol=normalized,
            version=version,
            status="complete" if not data_quality_flags else "complete_with_flags",
            confidence_level=level,
            confidence_score=confidence_score,
            template_version=TEMPLATE_VERSION,
            model_version=MODEL_VERSION,
            data_snapshot_id=data_snapshot_id,
            generated_at=generated_at,
            processing_duration_ms=processing_duration_ms,
        ),
        title=f"{normalized} Institutional Research Report",
        executive_summary=executive_summary,
        sections=sections,
        bull_case=thesis.bull_case,
        bear_case=thesis.bear_case,
        risks=thesis.risks,
        opportunities=[
            "Monitor improving evidence quality and market confirmation.",
            "Use watchlists and portfolio context to track material changes.",
        ],
        evidence=evidence_items,
        data_quality_flags=data_quality_flags,
        assumptions=[
            "This report is AI-assisted research support and not investment advice.",
            "Confidence reflects available evidence quality, not certainty of future returns.",
        ],
    )

    if persist:
        persist_research_report(db=db, user=user, report=report)
    return report


def persist_research_report(db: Session, user: User, report: ResearchReport) -> ResearchReportModel:
    model = ResearchReportModel(
        report_id=report.metadata.report_id,
        user_id=user.id,
        symbol=report.metadata.symbol,
        version=report.metadata.version,
        title=report.title,
        status=report.metadata.status,
        confidence_level=report.metadata.confidence_level,
        confidence_score=str(report.metadata.confidence_score),
        template_version=report.metadata.template_version,
        model_version=report.metadata.model_version,
        data_snapshot_id=report.metadata.data_snapshot_id,
        executive_summary=report.executive_summary,
        report_payload=report.model_dump(mode="json"),
        evidence_payload=[item.model_dump(mode="json") for item in report.evidence],
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


def list_research_reports(db: Session, user: User, symbol: str | None = None) -> list[ResearchReportRead]:
    statement = select(ResearchReportModel).where(ResearchReportModel.user_id == user.id)
    if symbol is not None:
        statement = statement.where(ResearchReportModel.symbol == symbol.strip().upper())
    statement = statement.order_by(ResearchReportModel.created_at.desc())
    reports = db.execute(statement).scalars().all()
    return [ResearchReportRead.model_validate(report) for report in reports]


def get_research_report(db: Session, user: User, report_id: str) -> ResearchReportRead | None:
    statement = select(ResearchReportModel).where(
        ResearchReportModel.user_id == user.id,
        ResearchReportModel.report_id == report_id,
    )
    report = db.execute(statement).scalars().first()
    if report is None:
        return None
    return ResearchReportRead.model_validate(report)
