from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.entity_resolution import KnowledgeEntityAlias
from app.models.knowledge_graph import KnowledgeEntity
from app.models.user import User
from app.schemas.entity_resolution import (
    DuplicateSuggestion,
    EntityAliasCreate,
    EntityAliasRead,
    EntityMergeRequest,
    EntityMergeResult,
)
from app.schemas.knowledge_graph import KnowledgeEntityRead
from app.services.entity_resolution_service import create_alias, merge_entities, normalize_alias, suggest_duplicates

router = APIRouter()


def _owned_entity(db: Session, owner_id: int, entity_id: int) -> KnowledgeEntity:
    entity = db.scalar(
        select(KnowledgeEntity).where(
            KnowledgeEntity.id == entity_id,
            KnowledgeEntity.owner_id == owner_id,
        )
    )
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


@router.post("/entities/{entity_id}/aliases", response_model=EntityAliasRead, status_code=status.HTTP_201_CREATED)
def add_entity_alias(
    entity_id: int,
    payload: EntityAliasCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeEntityAlias:
    entity = _owned_entity(db, current_user.id, entity_id)
    try:
        alias = create_alias(
            db,
            current_user.id,
            entity.id,
            payload.alias,
            payload.alias_type,
            payload.confidence,
            payload.provenance,
        )
        db.commit()
        db.refresh(alias)
        return alias
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/aliases/search", response_model=list[KnowledgeEntityRead])
def search_aliases(
    q: str = Query(min_length=1, max_length=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[KnowledgeEntity]:
    normalized = normalize_alias(q)
    alias_ids = select(KnowledgeEntityAlias.entity_id).where(
        KnowledgeEntityAlias.owner_id == current_user.id,
        KnowledgeEntityAlias.normalized_alias.ilike(f"%{normalized}%"),
    )
    return list(
        db.scalars(
            select(KnowledgeEntity)
            .where(
                KnowledgeEntity.owner_id == current_user.id,
                or_(KnowledgeEntity.id.in_(alias_ids), KnowledgeEntity.name.ilike(f"%{q}%")),
            )
            .order_by(KnowledgeEntity.name)
            .limit(50)
        ).all()
    )


@router.get("/entities/{entity_id}/duplicates", response_model=list[DuplicateSuggestion])
def get_duplicate_suggestions(
    entity_id: int,
    limit: int = Query(default=10, ge=1, le=25),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DuplicateSuggestion]:
    entity = _owned_entity(db, current_user.id, entity_id)
    return [
        DuplicateSuggestion(entity=candidate, score=score, reasons=reasons)
        for candidate, score, reasons in suggest_duplicates(db, current_user.id, entity, limit)
    ]


@router.post("/entities/{canonical_entity_id}/merge", response_model=EntityMergeResult)
def merge_duplicate_entity(
    canonical_entity_id: int,
    payload: EntityMergeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EntityMergeResult:
    canonical = _owned_entity(db, current_user.id, canonical_entity_id)
    duplicate = _owned_entity(db, current_user.id, payload.duplicate_entity_id)
    try:
        aliases, moved, audit = merge_entities(db, current_user.id, canonical, duplicate, payload.reason)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Merge creates a conflicting relationship or alias") from exc
    return EntityMergeResult(
        canonical_entity=canonical,
        aliases_created=aliases,
        relationships_moved=moved,
        audit_id=audit.id,
    )
