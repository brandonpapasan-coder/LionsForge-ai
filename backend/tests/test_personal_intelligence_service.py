from datetime import datetime, timedelta
from types import SimpleNamespace

from app.services.personal_intelligence_service import rank_personal_intelligence_memories


def _memory(
    memory_id: int,
    *,
    category: str,
    status: str = "validated",
    confidence: float = 0.8,
    statement: str = "Evidence-backed research finding",
    updated_offset: int = 0,
):
    return SimpleNamespace(
        id=memory_id,
        project_id=10,
        category=category,
        status=status,
        confidence=confidence,
        statement=statement,
        summary=statement,
        provenance={"source": "test"},
        updated_at=datetime(2026, 7, 18) + timedelta(minutes=updated_offset),
    )


def test_research_context_prefers_research_categories_and_query_overlap():
    memories = [
        _memory(1, category="mentor_preference", statement="Prefer short lessons"),
        _memory(2, category="validated_finding", statement="Battery evidence supports the hypothesis"),
    ]

    items = rank_personal_intelligence_memories(
        memories,
        audience="research_assistant",
        query="battery evidence",
        limit=10,
        include_provisional=False,
    )

    assert [item.memory_id for item in items] == [2, 1]
    assert items[0].relevance_score > items[1].relevance_score


def test_mentor_context_prefers_learning_categories():
    memories = [
        _memory(1, category="verified_fact"),
        _memory(2, category="misconception", statement="Learner confuses correlation with causation"),
    ]

    items = rank_personal_intelligence_memories(
        memories,
        audience="ai_mentor",
        query=None,
        limit=10,
        include_provisional=False,
    )

    assert [item.memory_id for item in items] == [2, 1]


def test_archived_superseded_and_provisional_memories_are_excluded_by_default():
    memories = [
        _memory(1, category="validated_finding", status="archived"),
        _memory(2, category="validated_finding", status="superseded"),
        _memory(3, category="validated_finding", status="provisional"),
        _memory(4, category="validated_finding", status="validated"),
    ]

    items = rank_personal_intelligence_memories(
        memories,
        audience="research_assistant",
        query=None,
        limit=10,
        include_provisional=False,
    )

    assert [item.memory_id for item in items] == [4]


def test_provisional_memories_can_be_included_explicitly():
    memories = [
        _memory(1, category="research_context", status="provisional", confidence=0.6),
        _memory(2, category="research_context", status="validated", confidence=0.7),
    ]

    items = rank_personal_intelligence_memories(
        memories,
        audience="research_assistant",
        query=None,
        limit=10,
        include_provisional=True,
    )

    assert {item.memory_id for item in items} == {1, 2}


def test_limit_is_enforced_and_trace_order_is_deterministic():
    memories = [
        _memory(1, category="validated_finding", updated_offset=1),
        _memory(2, category="validated_finding", updated_offset=2),
        _memory(3, category="validated_finding", updated_offset=3),
    ]

    items = rank_personal_intelligence_memories(
        memories,
        audience="research_assistant",
        query=None,
        limit=2,
        include_provisional=False,
    )

    assert [item.memory_id for item in items] == [3, 2]
