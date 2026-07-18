from importlib import import_module
from typing import Any

from app.models.company import Company
from app.models.education import LessonProgress
from app.models.entity_resolution import KnowledgeEntityAlias, KnowledgeEntityMergeAudit
from app.models.evidence import EvidenceRecord, EvidenceReviewEvent, ResearchReviewAction, ResearchReviewActionHistory
from app.models.executive_brief_snapshot import ExecutiveBriefSnapshot
from app.models.knowledge_federation import KnowledgeFederationLink, KnowledgeFederationRevision
from app.models.knowledge_graph import KnowledgeEntity, KnowledgeRelationship
from app.models.knowledge_memory import KnowledgeMemory, KnowledgeMemoryRevision
from app.models.mentor import MentorConversation, MentorMessage
from app.models.mission import Mission, MissionStep
from app.models.research_conclusion import ResearchConclusion, ResearchConclusionRevision
from app.models.research_conclusion_defense import ResearchConclusionDefense, ResearchConclusionDefenseRevision
from app.models.research_evidence import ResearchEvidence
from app.models.research_planning import ResearchPlanRecommendation, ResearchPlanRevision
from app.models.research_project import ResearchProject
from app.models.research_session import ResearchSession
from app.models.user import User

_LEGACY_EXPORTS = {
    "Alert": ("app.models.alert", "Alert"),
    "MarketLearningEvidenceLink": ("app.models.market_simulator", "MarketLearningEvidenceLink"),
    "MarketLearningSession": ("app.models.market_simulator", "MarketLearningSession"),
    "Portfolio": ("app.models.portfolio", "Portfolio"),
    "PortfolioHolding": ("app.models.portfolio", "PortfolioHolding"),
    "SimulatedTrade": ("app.models.market_simulator", "SimulatedTrade"),
    "SimulationAccount": ("app.models.market_simulator", "SimulationAccount"),
    "VirtualPosition": ("app.models.market_simulator", "VirtualPosition"),
    "Watchlist": ("app.models.watchlist", "Watchlist"),
}


def __getattr__(name: str) -> Any:
    target = _LEGACY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attribute_name = target
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value


__all__ = [
    "Alert",
    "Company",
    "EvidenceRecord",
    "EvidenceReviewEvent",
    "ExecutiveBriefSnapshot",
    "KnowledgeEntity",
    "KnowledgeEntityAlias",
    "KnowledgeEntityMergeAudit",
    "KnowledgeFederationLink",
    "KnowledgeFederationRevision",
    "KnowledgeMemory",
    "KnowledgeMemoryRevision",
    "KnowledgeRelationship",
    "LessonProgress",
    "MarketLearningEvidenceLink",
    "MarketLearningSession",
    "MentorConversation",
    "MentorMessage",
    "Mission",
    "MissionStep",
    "Portfolio",
    "PortfolioHolding",
    "ResearchConclusion",
    "ResearchConclusionDefense",
    "ResearchConclusionDefenseRevision",
    "ResearchConclusionRevision",
    "ResearchEvidence",
    "ResearchPlanRecommendation",
    "ResearchPlanRevision",
    "ResearchProject",
    "ResearchReviewAction",
    "ResearchReviewActionHistory",
    "ResearchSession",
    "SimulatedTrade",
    "SimulationAccount",
    "User",
    "VirtualPosition",
    "Watchlist",
]
