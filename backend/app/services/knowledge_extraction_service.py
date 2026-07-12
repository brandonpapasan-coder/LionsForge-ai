import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.knowledge_graph import KnowledgeEntity, KnowledgeRelationship
from app.schemas.knowledge_extraction import (
    ExtractedEntityCandidate,
    ExtractedRelationshipCandidate,
    KnowledgeExtractionRequest,
    KnowledgeExtractionResponse,
)


@dataclass(frozen=True)
class RelationshipPattern:
    phrase: str
    relationship_type: str


RELATIONSHIP_PATTERNS = (
    RelationshipPattern(" supplies ", "SUPPLIES"),
    RelationshipPattern(" supplied by ", "SUPPLIED_BY"),
    RelationshipPattern(" acquired ", "ACQUIRED"),
    RelationshipPattern(" partners with ", "PARTNERS_WITH"),
    RelationshipPattern(" partnered with ", "PARTNERS_WITH"),
    RelationshipPattern(" competes with ", "COMPETES_WITH"),
    RelationshipPattern(" depends on ", "DEPENDS_ON"),
    RelationshipPattern(" regulates ", "REGULATES"),
    RelationshipPattern(" invested in ", "INVESTED_IN"),
)

ORGANIZATION_SUFFIXES = (
    "Inc",
    "Incorporated",
    "Corp",
    "Corporation",
    "Company",
    "Co",
    "Ltd",
    "Limited",
    "LLC",
    "PLC",
    "Group",
    "Holdings",
    "University",
    "Agency",
    "Commission",
    "Department",
)

TECHNOLOGY_TERMS = {
    "artificial intelligence",
    "machine learning",
    "quantum computing",
    "semiconductors",
    "cloud computing",
    "robotics",
    "nuclear fusion",
    "battery storage",
}


def _normalize_name(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip(" ,.;:()[]{}\n\t"))


def _temporary_id(entity_type: str, name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return f"{entity_type}:{slug}"


def _extract_entities(content: str) -> list[ExtractedEntityCandidate]:
    found: dict[tuple[str, str], ExtractedEntityCandidate] = {}

    suffix_pattern = "|".join(re.escape(item) for item in ORGANIZATION_SUFFIXES)
    organization_regex = re.compile(
        rf"\b([A-Z][A-Za-z0-9&.'-]*(?:\s+[A-Z][A-Za-z0-9&.'-]*){{0,5}}\s+(?:{suffix_pattern})\.?)\b"
    )
    for match in organization_regex.finditer(content):
        name = _normalize_name(match.group(1))
        key = ("organization", name.casefold())
        found[key] = ExtractedEntityCandidate(
            temporary_id=_temporary_id("organization", name),
            entity_type="organization",
            name=name,
            confidence=0.86,
            evidence=match.group(0),
        )

    ticker_regex = re.compile(r"(?:\$|\()([A-Z]{2,5})(?:\))?\b")
    for match in ticker_regex.finditer(content):
        name = match.group(1)
        key = ("ticker", name)
        found[key] = ExtractedEntityCandidate(
            temporary_id=_temporary_id("ticker", name),
            entity_type="ticker",
            name=name,
            confidence=0.9,
            evidence=match.group(0),
        )

    lowered = content.lower()
    for term in TECHNOLOGY_TERMS:
        if term in lowered:
            name = term.title()
            key = ("technology", name.casefold())
            found[key] = ExtractedEntityCandidate(
                temporary_id=_temporary_id("technology", name),
                entity_type="technology",
                name=name,
                confidence=0.78,
                evidence=term,
            )

    return sorted(found.values(), key=lambda item: (item.entity_type, item.name.casefold()))


def _extract_relationships(
    content: str,
    entities: list[ExtractedEntityCandidate],
) -> list[ExtractedRelationshipCandidate]:
    by_name = sorted(entities, key=lambda item: len(item.name), reverse=True)
    relationships: dict[tuple[str, str, str], ExtractedRelationshipCandidate] = {}
    lowered = content.lower()

    for source in by_name:
        for target in by_name:
            if source.temporary_id == target.temporary_id:
                continue
            source_name = source.name.lower()
            target_name = target.name.lower()
            source_position = lowered.find(source_name)
            target_position = lowered.find(target_name, source_position + len(source_name))
            if source_position < 0 or target_position < 0:
                continue
            segment = lowered[source_position : target_position + len(target_name)]
            if len(segment) > 300:
                continue
            for pattern in RELATIONSHIP_PATTERNS:
                if pattern.phrase in segment:
                    evidence = content[source_position : target_position + len(target.name)].strip()
                    key = (source.temporary_id, target.temporary_id, pattern.relationship_type)
                    relationships[key] = ExtractedRelationshipCandidate(
                        source_temporary_id=source.temporary_id,
                        target_temporary_id=target.temporary_id,
                        relationship_type=pattern.relationship_type,
                        confidence=0.72,
                        evidence=evidence,
                    )
                    break

    return sorted(
        relationships.values(),
        key=lambda item: (item.source_temporary_id, item.target_temporary_id, item.relationship_type),
    )


def extract_knowledge_candidates(payload: KnowledgeExtractionRequest) -> KnowledgeExtractionResponse:
    entities = _extract_entities(payload.content)
    relationships = _extract_relationships(payload.content, entities)
    return KnowledgeExtractionResponse(
        entities=entities,
        relationships=relationships,
        limitations=[
            "Rule-based extraction can miss aliases, pronouns, and relationships expressed indirectly.",
            "Extracted candidates are unverified and require human or corroborating evidence review.",
        ],
    )


def extract_and_optionally_persist(
    db: Session,
    owner_id: int,
    payload: KnowledgeExtractionRequest,
) -> KnowledgeExtractionResponse:
    result = extract_knowledge_candidates(payload)
    if not payload.persist:
        return result

    source_metadata = {
        "source_title": payload.source_title,
        "source_url": payload.source_url,
        "method": "deterministic-rule-extraction",
    }
    persisted_entities: list[KnowledgeEntity] = []
    persisted_relationships: list[KnowledgeRelationship] = []
    entity_map: dict[str, KnowledgeEntity] = {}

    for candidate in result.entities:
        entity = db.scalar(
            select(KnowledgeEntity).where(
                KnowledgeEntity.owner_id == owner_id,
                KnowledgeEntity.entity_type == candidate.entity_type,
                KnowledgeEntity.name == candidate.name,
            )
        )
        if entity is None:
            entity = KnowledgeEntity(
                owner_id=owner_id,
                entity_type=candidate.entity_type,
                name=candidate.name,
                confidence=candidate.confidence,
                validation_status="unverified",
                provenance={**source_metadata, "evidence": candidate.evidence},
                attributes={"extraction_temporary_id": candidate.temporary_id},
            )
            db.add(entity)
            try:
                db.flush()
            except IntegrityError:
                db.rollback()
                entity = db.scalar(
                    select(KnowledgeEntity).where(
                        KnowledgeEntity.owner_id == owner_id,
                        KnowledgeEntity.entity_type == candidate.entity_type,
                        KnowledgeEntity.name == candidate.name,
                    )
                )
                if entity is None:
                    raise
        entity_map[candidate.temporary_id] = entity
        persisted_entities.append(entity)

    for candidate in result.relationships:
        source = entity_map.get(candidate.source_temporary_id)
        target = entity_map.get(candidate.target_temporary_id)
        if source is None or target is None:
            continue
        relationship = db.scalar(
            select(KnowledgeRelationship).where(
                KnowledgeRelationship.owner_id == owner_id,
                KnowledgeRelationship.source_entity_id == source.id,
                KnowledgeRelationship.target_entity_id == target.id,
                KnowledgeRelationship.relationship_type == candidate.relationship_type,
            )
        )
        if relationship is None:
            relationship = KnowledgeRelationship(
                owner_id=owner_id,
                source_entity_id=source.id,
                target_entity_id=target.id,
                relationship_type=candidate.relationship_type,
                confidence=candidate.confidence,
                validation_status="unverified",
                provenance={**source_metadata, "evidence": candidate.evidence},
                attributes={"extraction_method": "deterministic-rule-extraction"},
            )
            db.add(relationship)
            db.flush()
        persisted_relationships.append(relationship)

    db.commit()
    for entity in persisted_entities:
        db.refresh(entity)
    for relationship in persisted_relationships:
        db.refresh(relationship)

    result.persisted_entities = persisted_entities
    result.persisted_relationships = persisted_relationships
    return result
