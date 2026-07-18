import hashlib
import json
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.knowledge_memory import KnowledgeMemory, KnowledgeMemoryRevision

USER_AUTHORED_METHODOLOGY_VERSION = "user-authored-memory-v1"
EVIDENCE_BACKED_CATEGORIES = {"mastery_signal"}
SECRET_PATTERNS = (
    re.compile(r"\b(?:sk|pk)-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\b(?:api[_ -]?key|access[_ -]?token|secret|password)\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


def contains_prohibited_secret(*values: str) -> bool:
    text = "\n".join(values)
    return any(pattern.search(text) is not None for pattern in SECRET_PATTERNS)


def validate_user_authored_revision(memory: KnowledgeMemory, changes: dict) -> None:
    if memory.provenance.get("origin") != "user_authored":
        return

    statement = changes.get("statement", memory.statement)
    summary = changes.get("summary", memory.summary)
    category = changes.get("category", memory.category)
    confidence = changes.get("confidence", memory.confidence)
    evidence_ids = changes.get("source_evidence_ids", memory.source_evidence_ids)
    status = changes.get("status", memory.status)

    if contains_prohibited_secret(statement, summary):
        raise ValueError("Memory content appears to contain a secret or credential")
    if status == "validated":
        raise ValueError("User-authored memory cannot be manually marked as validated")
    if category in EVIDENCE_BACKED_CATEGORIES and (
        not evidence_ids or not memory.provenance.get("basis")
    ):
        raise ValueError("Evidence-backed memory requires evidence IDs and provenance basis")
    if not 0 <= confidence <= 1:
        raise ValueError("Memory confidence must be between 0 and 1")


def _fingerprint(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def create_user_authored_memory(
    db: Session,
    *,
    owner_id: int,
    project_id: int,
    statement: str,
    summary: str,
    category: str,
    confidence: float,
    source_evidence_ids: list[int],
    provenance: dict,
) -> tuple[KnowledgeMemory, bool]:
    if contains_prohibited_secret(statement, summary, json.dumps(provenance, sort_keys=True)):
        raise ValueError("Memory content appears to contain a secret or credential")

    if category in EVIDENCE_BACKED_CATEGORIES and (
        not source_evidence_ids or not provenance.get("basis")
    ):
        raise ValueError("Evidence-backed memory requires evidence IDs and provenance basis")

    normalized_statement = " ".join(statement.split())
    normalized_summary = " ".join(summary.split())
    normalized_provenance = {
        **provenance,
        "origin": "user_authored",
        "memory_methodology_version": USER_AUTHORED_METHODOLOGY_VERSION,
    }
    state = {
        "project_id": project_id,
        "statement": normalized_statement.casefold(),
        "summary": normalized_summary.casefold(),
        "category": category,
        "confidence": confidence,
        "source_evidence_ids": sorted(set(source_evidence_ids)),
        "provenance": normalized_provenance,
    }
    fingerprint = _fingerprint(state)
    existing = db.scalar(
        select(KnowledgeMemory).where(
            KnowledgeMemory.owner_id == owner_id,
            KnowledgeMemory.project_id == project_id,
            KnowledgeMemory.fingerprint == fingerprint,
        )
    )
    if existing is not None:
        return existing, False

    memory = KnowledgeMemory(
        owner_id=owner_id,
        project_id=project_id,
        mission_id=None,
        snapshot_id=None,
        fingerprint=fingerprint,
        statement=normalized_statement,
        summary=normalized_summary,
        category=category,
        status="provisional",
        confidence=confidence,
        source_evidence_ids=sorted(set(source_evidence_ids)),
        provenance=normalized_provenance,
    )
    db.add(memory)
    db.flush()
    db.add(
        KnowledgeMemoryRevision(
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
    )
    db.commit()
    db.refresh(memory)
    return memory, True
