import re
from difflib import SequenceMatcher

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.entity_resolution import KnowledgeEntityAlias, KnowledgeEntityMergeAudit
from app.models.knowledge_graph import KnowledgeEntity, KnowledgeRelationship

CORPORATE_SUFFIXES = {
    "inc",
    "incorporated",
    "corp",
    "corporation",
    "company",
    "co",
    "ltd",
    "limited",
    "llc",
    "plc",
    "holdings",
    "group",
}


def normalize_alias(value: str) -> str:
    tokens = re.findall(r"[a-z0-9]+", value.casefold())
    filtered = [token for token in tokens if token not in CORPORATE_SUFFIXES]
    return " ".join(filtered or tokens)


def create_alias(
    db: Session,
    owner_id: int,
    entity_id: int,
    alias: str,
    alias_type: str = "name",
    confidence: float = 1.0,
    provenance: dict | None = None,
) -> KnowledgeEntityAlias:
    normalized = normalize_alias(alias)
    existing = db.scalar(
        select(KnowledgeEntityAlias).where(
            KnowledgeEntityAlias.owner_id == owner_id,
            KnowledgeEntityAlias.normalized_alias == normalized,
        )
    )
    if existing:
        if existing.entity_id != entity_id:
            raise ValueError("Alias already resolves to another entity")
        return existing

    item = KnowledgeEntityAlias(
        owner_id=owner_id,
        entity_id=entity_id,
        alias=alias.strip(),
        normalized_alias=normalized,
        alias_type=alias_type,
        confidence=confidence,
        provenance=provenance or {},
    )
    db.add(item)
    db.flush()
    return item


def suggest_duplicates(
    db: Session,
    owner_id: int,
    entity: KnowledgeEntity,
    limit: int = 10,
) -> list[tuple[KnowledgeEntity, float, list[str]]]:
    candidates = list(
        db.scalars(
            select(KnowledgeEntity).where(
                KnowledgeEntity.owner_id == owner_id,
                KnowledgeEntity.id != entity.id,
                KnowledgeEntity.entity_type == entity.entity_type,
            )
        ).all()
    )
    source = normalize_alias(entity.name)
    suggestions: list[tuple[KnowledgeEntity, float, list[str]]] = []
    for candidate in candidates:
        target = normalize_alias(candidate.name)
        score = SequenceMatcher(None, source, target).ratio()
        reasons: list[str] = []
        if source == target:
            score = 1.0
            reasons.append("normalized names match")
        elif score >= 0.75:
            reasons.append("names are highly similar")
        if score >= 0.75:
            suggestions.append((candidate, round(score, 4), reasons))
    suggestions.sort(key=lambda item: item[1], reverse=True)
    return suggestions[:limit]


def merge_entities(
    db: Session,
    owner_id: int,
    canonical: KnowledgeEntity,
    duplicate: KnowledgeEntity,
    reason: str | None = None,
) -> tuple[list[KnowledgeEntityAlias], int, KnowledgeEntityMergeAudit]:
    if canonical.id == duplicate.id:
        raise ValueError("Cannot merge an entity into itself")
    if canonical.entity_type != duplicate.entity_type:
        raise ValueError("Entities must share the same type")

    snapshot = {
        "id": duplicate.id,
        "entity_type": duplicate.entity_type,
        "name": duplicate.name,
        "description": duplicate.description,
        "confidence": duplicate.confidence,
        "validation_status": duplicate.validation_status,
        "provenance": duplicate.provenance,
        "attributes": duplicate.attributes,
    }

    created_aliases: list[KnowledgeEntityAlias] = []
    for alias_value, alias_type in ((duplicate.name, "name"),):
        try:
            created_aliases.append(
                create_alias(
                    db,
                    owner_id,
                    canonical.id,
                    alias_value,
                    alias_type,
                    duplicate.confidence,
                    {"merged_from_entity_id": duplicate.id, "source": duplicate.provenance},
                )
            )
        except ValueError:
            pass

    duplicate_aliases = list(
        db.scalars(
            select(KnowledgeEntityAlias).where(
                KnowledgeEntityAlias.owner_id == owner_id,
                KnowledgeEntityAlias.entity_id == duplicate.id,
            )
        ).all()
    )
    for alias in duplicate_aliases:
        alias.entity_id = canonical.id
        created_aliases.append(alias)

    relationships = list(
        db.scalars(
            select(KnowledgeRelationship).where(
                KnowledgeRelationship.owner_id == owner_id,
                or_(
                    KnowledgeRelationship.source_entity_id == duplicate.id,
                    KnowledgeRelationship.target_entity_id == duplicate.id,
                ),
            )
        ).all()
    )
    moved_ids: list[int] = []
    for relationship in relationships:
        if relationship.source_entity_id == duplicate.id:
            relationship.source_entity_id = canonical.id
        if relationship.target_entity_id == duplicate.id:
            relationship.target_entity_id = canonical.id
        if relationship.source_entity_id == relationship.target_entity_id:
            db.delete(relationship)
            continue
        moved_ids.append(relationship.id)

    canonical.provenance = {
        **(canonical.provenance or {}),
        "merged_entities": [
            *((canonical.provenance or {}).get("merged_entities", [])),
            snapshot,
        ],
    }
    canonical.confidence = max(canonical.confidence, duplicate.confidence)
    db.flush()

    audit = KnowledgeEntityMergeAudit(
        owner_id=owner_id,
        canonical_entity_id=canonical.id,
        merged_entity_snapshot=snapshot,
        moved_relationship_ids=moved_ids,
        created_alias_ids=[alias.id for alias in created_aliases if alias.id],
        reason=reason,
    )
    db.add(audit)
    db.delete(duplicate)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(canonical)
    db.refresh(audit)
    return created_aliases, len(moved_ids), audit
