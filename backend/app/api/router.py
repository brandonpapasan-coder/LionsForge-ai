from fastapi import APIRouter

from app.api.routes import (
    auth,
    dashboard,
    education,
    entity_resolution,
    evidence_intelligence,
    executive_intelligence,
    investigations,
    knowledge_extraction,
    knowledge_federation,
    knowledge_graph,
    knowledge_memory,
    knowledge_memory_evidence,
    knowledge_memory_remediation,
    knowledge_memory_remediation_escalation,
    knowledge_memory_remediation_verification,
    knowledge_quality,
    mentor,
    missions,
    multi_agent_consensus,
    news,
    personal_intelligence,
    release_countdown,
    research,
    research_agent,
    research_conclusion_defense_export_packet,
    research_conclusion_defense_review,
    research_conclusion_export_packet,
    research_conclusion_readiness,
    research_conclusion_workspace,
    research_evidence,
    research_evidence_audit_packet,
    research_evidence_provenance,
    research_follow_up_tracker,
    research_governance_dashboard,
    research_governance_digest,
    research_orchestration,
    research_packet_comparison,
    research_packet_comparison_report,
    research_packet_comparison_report_chain,
    research_packet_comparison_report_chain_export,
    research_packet_comparison_report_chain_export_integrity,
    research_packet_comparison_report_chain_export_integrity_receipt,
    research_packet_comparison_report_chain_export_integrity_receipt_integrity,
    research_packet_comparison_report_integrity,
    research_packet_integrity,
    research_planning,
    research_projects,
    research_sessions,
    research_trust_index,
    system,
    user_authored_memory,
)
from app.core.config import Settings, get_settings
from app.core.legacy_finance_config import LegacyFinanceSettings, get_legacy_finance_settings


def build_api_router(
    settings: Settings | None = None,
    legacy_finance_settings: LegacyFinanceSettings | None = None,
) -> APIRouter:
    resolved_settings = settings or get_settings()
    resolved_legacy_finance_settings = legacy_finance_settings or get_legacy_finance_settings()
    router = APIRouter()

    router.include_router(auth.router, prefix="/auth", tags=["auth"])
    router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
    router.include_router(release_countdown.router, prefix="/release-countdown", tags=["release-countdown"])
    router.include_router(education.router, prefix="/education", tags=["education"])
    router.include_router(investigations.router, prefix="/investigations", tags=["investigations"])
    router.include_router(knowledge_graph.router, prefix="/knowledge-graph", tags=["knowledge-graph"])
    router.include_router(knowledge_extraction.router, prefix="/knowledge-graph", tags=["knowledge-extraction"])
    router.include_router(entity_resolution.router, prefix="/knowledge-graph", tags=["entity-resolution"])
    router.include_router(knowledge_memory.router, prefix="/knowledge-memory", tags=["knowledge-memory"])
    router.include_router(knowledge_memory_evidence.router, prefix="/knowledge-memory", tags=["knowledge-memory"])
    router.include_router(knowledge_memory_remediation.router, prefix="/knowledge-memory", tags=["knowledge-memory"])
    router.include_router(knowledge_memory_remediation_escalation.router, prefix="/knowledge-memory", tags=["knowledge-memory"])
    router.include_router(knowledge_memory_remediation_verification.router, prefix="/knowledge-memory", tags=["knowledge-memory"])
    router.include_router(user_authored_memory.router, prefix="/knowledge-memory/user-authored", tags=["knowledge-memory"])
    router.include_router(personal_intelligence.router, prefix="/personal-intelligence", tags=["personal-intelligence"])
    router.include_router(knowledge_federation.router, prefix="/knowledge-federation", tags=["knowledge-federation"])
    router.include_router(knowledge_quality.router, prefix="/knowledge-quality", tags=["knowledge-quality"])
    router.include_router(research_planning.router, prefix="/research-planning", tags=["research-planning"])
    router.include_router(evidence_intelligence.router, prefix="/evidence-intelligence", tags=["evidence-intelligence"])
    router.include_router(research_evidence_provenance.router, prefix="/research-evidence-provenance", tags=["research-evidence-provenance"])
    router.include_router(research_evidence_audit_packet.router, prefix="/research-evidence-audit", tags=["research-evidence-audit"])
    router.include_router(research_follow_up_tracker.router, prefix="/research-follow-up", tags=["research-follow-up"])
    router.include_router(research_conclusion_readiness.router, prefix="/research-conclusion-readiness", tags=["research-conclusion-readiness"])
    router.include_router(research_conclusion_workspace.router, prefix="/research-conclusions", tags=["research-conclusions"])
    router.include_router(research_conclusion_export_packet.router, prefix="/research-conclusion-export", tags=["research-conclusion-export"])
    router.include_router(research_conclusion_defense_review.router, prefix="/research-conclusion-defense", tags=["research-conclusion-defense"])
    router.include_router(research_conclusion_defense_export_packet.router, prefix="/research-conclusion-defense-export", tags=["research-conclusion-defense-export"])
    router.include_router(research_packet_integrity.router, prefix="/research-packet-integrity", tags=["research-packet-integrity"])
    router.include_router(research_packet_comparison.router, prefix="/research-packet-comparison", tags=["research-packet-comparison"])
    router.include_router(research_packet_comparison_report.router, prefix="/research-packet-comparison-report", tags=["research-packet-comparison-report"])
    router.include_router(research_packet_comparison_report_integrity.router, prefix="/research-packet-comparison-report-integrity", tags=["research-packet-comparison-report-integrity"])
    router.include_router(research_packet_comparison_report_chain.router, prefix="/research-packet-comparison-report-chain", tags=["research-packet-comparison-report-chain"])
    router.include_router(research_packet_comparison_report_chain_export.router, prefix="/research-packet-comparison-report-chain-export", tags=["research-packet-comparison-report-chain-export"])
    router.include_router(research_packet_comparison_report_chain_export_integrity.router, prefix="/research-packet-comparison-report-chain-export-integrity", tags=["research-packet-comparison-report-chain-export-integrity"])
    router.include_router(research_packet_comparison_report_chain_export_integrity_receipt.router, prefix="/research-packet-comparison-report-chain-export-integrity-receipt", tags=["research-packet-comparison-report-chain-export-integrity-receipt"])
    router.include_router(research_packet_comparison_report_chain_export_integrity_receipt_integrity.router, prefix="/research-packet-comparison-report-chain-export-integrity-receipt-check", tags=["research-packet-comparison-report-chain-export-integrity-receipt-check"])
    router.include_router(research_governance_dashboard.router, prefix="/research-governance-dashboard", tags=["research-governance-dashboard"])
    router.include_router(research_governance_digest.router, prefix="/research-governance-digest", tags=["research-governance-digest"])
    router.include_router(research_trust_index.router, prefix="/research-trust-index", tags=["research-trust-index"])
    router.include_router(multi_agent_consensus.router, prefix="/multi-agent-consensus", tags=["multi-agent-consensus"])
    router.include_router(research_orchestration.router, prefix="/research-orchestration", tags=["research-orchestration"])
    router.include_router(executive_intelligence.router, prefix="/executive-intelligence", tags=["executive-intelligence"])
    router.include_router(missions.router, prefix="/missions", tags=["missions"])
    router.include_router(mentor.router, prefix="/mentor", tags=["mentor"])
    router.include_router(research.router, prefix="/research", tags=["research"])
    router.include_router(research_agent.router, prefix="/research-agent", tags=["research-agent"])
    router.include_router(research_projects.router, prefix="/research-projects", tags=["research-projects"])
    router.include_router(research_sessions.router, tags=["research-sessions"])
    router.include_router(research_evidence.router, tags=["research-evidence"])
    router.include_router(news.router, prefix="/news", tags=["news"])
    router.include_router(system.router, prefix="/system", tags=["system"])

    if resolved_legacy_finance_settings.enable_legacy_finance_modules:
        from app.api.routes import (
            advanced_alerts,
            alerts,
            autonomous_portfolios,
            companies,
            decisions,
            events,
            factors,
            market,
            market_learning,
            market_learning_evidence,
            market_learning_mastery,
            market_learning_portfolio,
            market_learning_progress,
            market_learning_roadmap,
            market_mentor,
            market_simulator,
            portfolios,
            watchlists,
        )

        router.include_router(market.router, prefix="/market", tags=["market"])
        router.include_router(market_simulator.router, prefix="/market-simulator", tags=["market-simulator"])
        router.include_router(market_mentor.router, prefix="/market-simulator", tags=["market-simulator-mentor"])
        router.include_router(market_learning.router, prefix="/market-simulator", tags=["market-simulator-learning"])
        router.include_router(market_learning_progress.router, prefix="/market-simulator", tags=["market-simulator-learning"])
        router.include_router(market_learning_evidence.router, prefix="/market-simulator", tags=["market-simulator-learning"])
        router.include_router(market_learning_portfolio.router, prefix="/market-simulator", tags=["market-simulator-learning"])
        router.include_router(market_learning_roadmap.router, prefix="/market-simulator", tags=["market-simulator-learning"])
        router.include_router(market_learning_mastery.router, prefix="/market-simulator", tags=["market-simulator-learning"])
        router.include_router(watchlists.router, prefix="/watchlists", tags=["watchlists"])
        router.include_router(portfolios.router, prefix="/portfolios", tags=["portfolios"])
        router.include_router(autonomous_portfolios.router, prefix="/portfolios", tags=["portfolio-intelligence"])
        router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
        router.include_router(advanced_alerts.router, prefix="/advanced-alerts", tags=["advanced-alerts"])
        router.include_router(companies.router, prefix="/companies", tags=["companies"])
        router.include_router(factors.router, prefix="/factors", tags=["factors"])
        router.include_router(events.router, prefix="/events", tags=["events"])
        router.include_router(decisions.router, prefix="/decisions", tags=["decisions"])

    return router


api_router = build_api_router()
