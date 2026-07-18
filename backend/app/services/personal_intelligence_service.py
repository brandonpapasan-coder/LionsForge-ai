from collections.abc import Iterable

from sqlalchemy.orm import Session

from app.models.knowledge_memory import KnowledgeMemory
from app.schemas.personal_intelligence import (
    PersonalIntelligenceAudience,
    PersonalIntelligenceContextItem,
    PersonalIntelligenceContextResponse,
)
from app.services.knowledge_memory_service import list_memories

_RESEARCH_CATEGORIES = {
    "executive_conclusion",
    "verified_fact",
    "provisional_conclusion",
    "minority_finding",
    "research_preference",
    "research_context",
    "validated_finding",
}

_EDUCATION_CATEGORIES = {
    "learning_goal",
    "mastery_signal",
    "misconception",
    "mentor_preference",
}


def _tokenize(value: str | None) -> set[str]:
    if not value:
        return set()
    return {
        token.strip(".,:;!?()[]{}\"'").lower()
        for token in value.split()
        if token.strip(".,:;!?()[]{}\"'")
    }


def _audience_bonus(memory: KnowledgeMemory, audience: PersonalIntelligenceAudience) -> float:
    categories = _RESEARCH_CATEGORIES if audience == "research_assistant" else _EDUCATION_CATEGORIES
    return 0.25 if memory.category in categories else 0.0


def _relevance_score(
    memory: KnowledgeMemory,
    audience: PersonalIntelligenceAudience,
    query_tokens: set[str],
) -> float:
    memory_tokens = _tokenize(f"{memory.statement} {memory.summary} {memory.category}")
    overlap = len(query_tokens & memory_tokens)
    query_component = min(overlap * 0.12, 0.36)
    status_component = {
        "validated": 0.25,
        "provisional": 0.08,
        "contested": 0.04,
    }.get(memory.status, 0.0)
    confidence_component = max(0.0, min(memory.confidence, 1.0)) * 0.14
    return round(_audience_bonus(memory, audience) + query_component + status_component + confidence_component, 4)


def rank_personal_intelligence_memories(
    memories: Iterable[KnowledgeMemory],
    audience: PersonalIntelligenceAudience,
    query: str | None,
    limit: int,
    include_provisional: bool,
) -> list[PersonalIntelligenceContextItem]:
    query_tokens = _tokenize(query)
    eligible = []
    for memory in memories:
        if memory.status in {"archived", "superseded"}:
            continue
        if not include_provisional and memory.status != "validated":
            continue
        eligible.append(memory)

    ranked = sorted(
        eligible,
        key=lambda memory: (
            _relevance_score(memory, audience, query_tokens),
            memory.updated_at,
            memory.id,
        ),
        reverse=True,
    )[:limit]

    return [
        PersonalIntelligenceContextItem(
            memory_id=memory.id,
            project_id=memory.project_id,
            category=memory.category,
            status=memory.status,
            confidence=memory.confidence,
            statement=memory.statement,
            summary=memory.summary,
            provenance=memory.provenance,
            relevance_score=_relevance_score(memory, audience, query_tokens),
        )
        for memory in ranked
    ]


def build_personal_intelligence_context(
    db: Session,
    owner_id: int,
    audience: PersonalIntelligenceAudience,
    project_id: int | None,
    query: str | None,
    limit: int,
    include_provisional: bool,
) -> PersonalIntelligenceContextResponse:
    memories = list_memories(db, owner_id, project_id=project_id)
    items = rank_personal_intelligence_memories(
        memories,
        audience=audience,
        query=query,
        limit=limit,
        include_provisional=include_provisional,
    )
    return PersonalIntelligenceContextResponse(
        audience=audience,
        items=items,
        trace_memory_ids=[item.memory_id for item in items],
    )
