import hashlib
import json
import re
from difflib import SequenceMatcher

from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from app.models.knowledge_federation import (
    KnowledgeFederationLink,
    KnowledgeFederationRevision,
)
from app.models.knowledge_memory import KnowledgeMemory

METHODOLOGY_VERSION = "knowledge-federation-v1"


def _normalize(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def _fingerprint(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _token_overlap(left: str, right: str) -> float:
    left_tokens = set(_normalize(left).split())
    right_tokens = set(_normalize(right).split())
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def score_pair(source: KnowledgeMemory, target: KnowledgeMemory) -> tuple[str, float, dict]:
    normalized_source = _normalize(source.statement)
    normalized_target = _normalize(target.statement)
    sequence = SequenceMatcher(None, normalized_source, normalized_target).ratio()
    token_overlap = _token_overlap(source.statement, target.statement)
    shared_evidence = len(set(source.source_evidence_ids) & set(target.source_evidence_ids))
    evidence_score = 1.0 if shared_evidence else 0.0
    category_score = 1.0 if source.category == target.category else 0.0
    confidence_alignment = 1.0 - abs(source.confidence - target.confidence)
    score = round(
        (sequence * 0.4)
        + (token_overlap * 0.25)
        + (evidence_score * 0.15)
        + (category_score * 0.1)
        + (confidence_alignment * 0.1),
        4,
    )
    opposite_states = {source.status, target.status} == {"validated", "contested"}
    if opposite_states and (sequence >= 0.55 or token_overlap >= 0.45):
        link_type = "contradicting"
    elif normalized_source == normalized_target or score >= 0.9:
        link_type = "duplicate"
    elif source.status == target.status == "validated" and score >= 0.6:
        link_type = "supporting"
    else:
        link_type = "related"
    return link_type, score, {
        "statement_similarity": round(sequence, 4),
        "token_overlap": round(token_overlap, 4),
        "shared_evidence_count": shared_evidence,
        "category_match": bool(category_score),
        "confidence_alignment": round(confidence_alignment, 4),
    }


def _revision(link: KnowledgeFederationLink) -> KnowledgeFederationRevision:
    return KnowledgeFederationRevision(
        link_id=link.id,
        revision_number=link.revision_number,
        link_type=link.link_type,
        score=link.score,
        score_components=link.score_components,
        provenance=link.provenance,
        status=link.status,
    )


def scan_project(db: Session, owner_id: int, project_id: int) -> tuple[list[KnowledgeFederationLink], int, int]:
    sources = list(db.scalars(select(KnowledgeMemory).where(KnowledgeMemory.owner_id == owner_id, KnowledgeMemory.project_id == project_id)).all())
    targets = list(db.scalars(select(KnowledgeMemory).where(KnowledgeMemory.owner_id == owner_id, KnowledgeMemory.project_id != project_id)).all())
    links: list[KnowledgeFederationLink] = []
    created = 0
    reused = 0
    for source in sources:
        for target in targets:
            link_type, score, components = score_pair(source, target)
            if score < 0.45:
                continue
            left_id, right_id = sorted((source.id, target.id))
            fingerprint = _fingerprint({"left": left_id, "right": right_id, "type": link_type, "methodology": METHODOLOGY_VERSION})
            existing = db.scalar(select(KnowledgeFederationLink).where(KnowledgeFederationLink.owner_id == owner_id, KnowledgeFederationLink.fingerprint == fingerprint))
            if existing:
                links.append(existing)
                reused += 1
                continue
            link = KnowledgeFederationLink(
                owner_id=owner_id,
                source_memory_id=source.id,
                target_memory_id=target.id,
                source_project_id=source.project_id,
                target_project_id=target.project_id,
                link_type=link_type,
                score=score,
                score_components=components,
                provenance={
                    "source_memory_revision": source.revision_number,
                    "target_memory_revision": target.revision_number,
                    "source_provenance": source.provenance,
                    "target_provenance": target.provenance,
                    "methodology_version": METHODOLOGY_VERSION,
                },
                fingerprint=fingerprint,
            )
            db.add(link)
            db.flush()
            db.add(_revision(link))
            links.append(link)
            created += 1
    db.commit()
    return links, created, reused


def list_links(db: Session, owner_id: int, project_id: int | None = None, link_type: str | None = None, status: str | None = None) -> list[KnowledgeFederationLink]:
    stmt = select(KnowledgeFederationLink).where(KnowledgeFederationLink.owner_id == owner_id)
    if project_id is not None:
        stmt = stmt.where(or_(KnowledgeFederationLink.source_project_id == project_id, KnowledgeFederationLink.target_project_id == project_id))
    if link_type is not None:
        stmt = stmt.where(KnowledgeFederationLink.link_type == link_type)
    if status is not None:
        stmt = stmt.where(KnowledgeFederationLink.status == status)
    return list(db.scalars(stmt.order_by(desc(KnowledgeFederationLink.score), desc(KnowledgeFederationLink.id))).all())
