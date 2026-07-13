import hashlib
import json

from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from app.models.executive_brief_snapshot import ExecutiveBriefSnapshot
from app.models.knowledge_memory import KnowledgeMemory, KnowledgeMemoryRevision
from app.models.mission import Mission

METHODOLOGY_VERSION = "knowledge-memory-v1"


def _fingerprint(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _revision(memory: KnowledgeMemory) -> KnowledgeMemoryRevision:
    return KnowledgeMemoryRevision(
        memory_id=memory.id,
        revision_number=memory.revision_number,
        statement=memory.statement,
        summary=memory.summary,
        category=memory.category,
        status=memory.status,
        confidence=memory.confidence,
        source_evidence_ids=memory.source_evidence_ids,
        provenance=memory.provenance,
    )


def promote_completed_mission(
    db: Session,
    owner_id: int,
    mission: Mission,
    snapshot: ExecutiveBriefSnapshot,
) -> tuple[list[KnowledgeMemory], int, int]:
    if mission.status != "completed" or mission.final_snapshot_id != snapshot.id:
        raise ValueError("Mission must be completed with the referenced final snapshot")

    brief = snapshot.payload
    candidates: list[dict] = [
        {
            "statement": brief["executive_summary"],
            "summary": brief["executive_summary"],
            "category": "executive_conclusion",
            "status": "validated" if brief["recommendation"] == "go" else "provisional",
            "confidence": brief["overall_confidence"],
            "source_evidence_ids": brief["source_evidence_ids"],
        }
    ]
    for fact in brief.get("verified_facts", []):
        candidates.append(
            {
                "statement": fact["statement"],
                "summary": fact["statement"],
                "category": "verified_fact",
                "status": "validated",
                "confidence": fact["confidence"],
                "source_evidence_ids": fact["evidence_ids"],
            }
        )
    for finding in brief.get("minority_findings", []):
        candidates.append(
            {
                "statement": finding,
                "summary": finding,
                "category": "minority_finding",
                "status": "contested",
                "confidence": min(brief["overall_confidence"], 0.7),
                "source_evidence_ids": brief["source_evidence_ids"],
            }
        )

    memories: list[KnowledgeMemory] = []
    created = 0
    reused = 0
    for candidate in candidates:
        provenance = {
            "mission_id": mission.id,
            "snapshot_id": snapshot.id,
            "project_id": mission.project_id,
            "mission_methodology_version": mission.methodology_version,
            "snapshot_methodology_version": snapshot.methodology_version,
            "memory_methodology_version": METHODOLOGY_VERSION,
            "recommendation": brief["recommendation"],
            "research_trust_index": brief["research_trust_index"],
            "consensus_status": brief["consensus_status"],
        }
        state = {**candidate, "provenance": provenance}
        fingerprint = _fingerprint(state)
        existing = db.scalar(
            select(KnowledgeMemory).where(
                KnowledgeMemory.owner_id == owner_id,
                KnowledgeMemory.project_id == mission.project_id,
                KnowledgeMemory.fingerprint == fingerprint,
            )
        )
        if existing is not None:
            memories.append(existing)
            reused += 1
            continue

        memory = KnowledgeMemory(
            owner_id=owner_id,
            project_id=mission.project_id,
            mission_id=mission.id,
            snapshot_id=snapshot.id,
            fingerprint=fingerprint,
            provenance=provenance,
            **candidate,
        )
        db.add(memory)
        db.flush()
        db.add(_revision(memory))
        memories.append(memory)
        created += 1

    db.commit()
    for memory in memories:
        db.refresh(memory)
    return memories, created, reused


def list_memories(
    db: Session,
    owner_id: int,
    project_id: int | None = None,
    status: str | None = None,
    category: str | None = None,
    mission_id: int | None = None,
    snapshot_id: int | None = None,
    query: str | None = None,
) -> list[KnowledgeMemory]:
    stmt = select(KnowledgeMemory).where(KnowledgeMemory.owner_id == owner_id)
    if project_id is not None:
        stmt = stmt.where(KnowledgeMemory.project_id == project_id)
    if status is not None:
        stmt = stmt.where(KnowledgeMemory.status == status)
    if category is not None:
        stmt = stmt.where(KnowledgeMemory.category == category)
    if mission_id is not None:
        stmt = stmt.where(KnowledgeMemory.mission_id == mission_id)
    if snapshot_id is not None:
        stmt = stmt.where(KnowledgeMemory.snapshot_id == snapshot_id)
    if query:
        pattern = f"%{query}%"
        stmt = stmt.where(
            or_(KnowledgeMemory.statement.ilike(pattern), KnowledgeMemory.summary.ilike(pattern))
        )
    return list(db.scalars(stmt.order_by(desc(KnowledgeMemory.updated_at), desc(KnowledgeMemory.id))).all())


def revisions_for(db: Session, memory_id: int) -> list[KnowledgeMemoryRevision]:
    return list(
        db.scalars(
            select(KnowledgeMemoryRevision)
            .where(KnowledgeMemoryRevision.memory_id == memory_id)
            .order_by(KnowledgeMemoryRevision.revision_number)
        ).all()
    )


def update_memory(db: Session, memory: KnowledgeMemory, changes: dict) -> KnowledgeMemory:
    changed = False
    for key, value in changes.items():
        if value is not None and getattr(memory, key) != value:
            setattr(memory, key, value)
            changed = True
    if not changed:
        return memory

    memory.revision_number += 1
    state = {
        "statement": memory.statement,
        "summary": memory.summary,
        "category": memory.category,
        "status": memory.status,
        "confidence": memory.confidence,
        "source_evidence_ids": memory.source_evidence_ids,
        "provenance": memory.provenance,
        "revision_number": memory.revision_number,
    }
    memory.fingerprint = _fingerprint(state)
    db.add(_revision(memory))
    db.commit()
    db.refresh(memory)
    return memory


def supersede_memory(db: Session, memory: KnowledgeMemory, replacement: KnowledgeMemory) -> KnowledgeMemory:
    if memory.project_id != replacement.project_id:
        raise ValueError("Memories must belong to the same project")
    if memory.id == replacement.id:
        raise ValueError("Memory cannot supersede itself")
    return update_memory(
        db,
        memory,
        {"status": "superseded", "superseded_by_id": replacement.id},
    )
