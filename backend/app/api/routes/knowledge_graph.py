from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.knowledge_graph import KnowledgeEntity, KnowledgeRelationship
from app.models.user import User
from app.schemas.knowledge_graph import (
    KnowledgeEntityCreate,
    KnowledgeEntityRead,
    KnowledgeGraphRead,
    KnowledgeRelationshipCreate,
    KnowledgeRelationshipRead,
)

router = APIRouter()


@router.get("", response_model=KnowledgeGraphRead)
def get_graph(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeGraphRead:
    entities = list(db.scalars(select(KnowledgeEntity).where(KnowledgeEntity.owner_id == current_user.id).order_by(KnowledgeEntity.name)).all())
    relationships = list(
        db.scalars(
            select(KnowledgeRelationship)
            .where(KnowledgeRelationship.owner_id == current_user.id)
            .order_by(KnowledgeRelationship.created_at)
        ).all()
    )
    return KnowledgeGraphRead(entities=entities, relationships=relationships)


@router.get("/search", response_model=list[KnowledgeEntityRead])
def search_entities(
    q: str = Query(min_length=1, max_length=200),
    entity_type: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[KnowledgeEntity]:
    statement = select(KnowledgeEntity).where(
        KnowledgeEntity.owner_id == current_user.id,
        or_(KnowledgeEntity.name.ilike(f"%{q}%"), KnowledgeEntity.description.ilike(f"%{q}%")),
    )
    if entity_type:
        statement = statement.where(KnowledgeEntity.entity_type == entity_type)
    return list(db.scalars(statement.order_by(KnowledgeEntity.name).limit(50)).all())


@router.post("/entities", response_model=KnowledgeEntityRead, status_code=status.HTTP_201_CREATED)
def create_entity(
    payload: KnowledgeEntityCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeEntity:
    entity = KnowledgeEntity(owner_id=current_user.id, **payload.model_dump())
    db.add(entity)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Entity already exists") from exc
    db.refresh(entity)
    return entity


@router.get("/entities/{entity_id}", response_model=KnowledgeEntityRead)
def get_entity(
    entity_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeEntity:
    entity = db.scalar(
        select(KnowledgeEntity).where(
            KnowledgeEntity.id == entity_id,
            KnowledgeEntity.owner_id == current_user.id,
        )
    )
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


@router.post("/relationships", response_model=KnowledgeRelationshipRead, status_code=status.HTTP_201_CREATED)
def create_relationship(
    payload: KnowledgeRelationshipCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeRelationship:
    entity_ids = {payload.source_entity_id, payload.target_entity_id}
    owned_ids = set(
        db.scalars(
            select(KnowledgeEntity.id).where(
                KnowledgeEntity.owner_id == current_user.id,
                KnowledgeEntity.id.in_(entity_ids),
            )
        ).all()
    )
    if owned_ids != entity_ids:
        raise HTTPException(status_code=404, detail="Source or target entity not found")

    relationship = KnowledgeRelationship(owner_id=current_user.id, **payload.model_dump())
    db.add(relationship)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Relationship already exists") from exc
    db.refresh(relationship)
    return relationship


@router.get("/entities/{entity_id}/relationships", response_model=list[KnowledgeRelationshipRead])
def get_entity_relationships(
    entity_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[KnowledgeRelationship]:
    entity = db.scalar(
        select(KnowledgeEntity.id).where(
            KnowledgeEntity.id == entity_id,
            KnowledgeEntity.owner_id == current_user.id,
        )
    )
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    return list(
        db.scalars(
            select(KnowledgeRelationship).where(
                KnowledgeRelationship.owner_id == current_user.id,
                or_(
                    KnowledgeRelationship.source_entity_id == entity_id,
                    KnowledgeRelationship.target_entity_id == entity_id,
                ),
            )
        ).all()
    )
