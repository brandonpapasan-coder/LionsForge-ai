from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
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
    KnowledgeEntityUpdate,
    KnowledgeGraphRead,
    KnowledgeRelationshipCreate,
    KnowledgeRelationshipRead,
    KnowledgeRelationshipUpdate,
    KnowledgeTraversalRead,
)

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


def _owned_relationship(db: Session, owner_id: int, relationship_id: int) -> KnowledgeRelationship:
    relationship = db.scalar(
        select(KnowledgeRelationship).where(
            KnowledgeRelationship.id == relationship_id,
            KnowledgeRelationship.owner_id == owner_id,
        )
    )
    if relationship is None:
        raise HTTPException(status_code=404, detail="Relationship not found")
    return relationship


@router.get("", response_model=KnowledgeGraphRead)
def get_graph(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeGraphRead:
    entities = list(
        db.scalars(
            select(KnowledgeEntity)
            .where(KnowledgeEntity.owner_id == current_user.id)
            .order_by(KnowledgeEntity.name)
        ).all()
    )
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
    return _owned_entity(db, current_user.id, entity_id)


@router.patch("/entities/{entity_id}", response_model=KnowledgeEntityRead)
def update_entity(
    entity_id: int,
    payload: KnowledgeEntityUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeEntity:
    entity = _owned_entity(db, current_user.id, entity_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(entity, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Entity already exists") from exc
    db.refresh(entity)
    return entity


@router.delete("/entities/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entity(
    entity_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    entity = _owned_entity(db, current_user.id, entity_id)
    db.delete(entity)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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


@router.get("/relationships/{relationship_id}", response_model=KnowledgeRelationshipRead)
def get_relationship(
    relationship_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeRelationship:
    return _owned_relationship(db, current_user.id, relationship_id)


@router.patch("/relationships/{relationship_id}", response_model=KnowledgeRelationshipRead)
def update_relationship(
    relationship_id: int,
    payload: KnowledgeRelationshipUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeRelationship:
    relationship = _owned_relationship(db, current_user.id, relationship_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(relationship, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Relationship already exists") from exc
    db.refresh(relationship)
    return relationship


@router.delete("/relationships/{relationship_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_relationship(
    relationship_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    relationship = _owned_relationship(db, current_user.id, relationship_id)
    db.delete(relationship)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/entities/{entity_id}/relationships", response_model=list[KnowledgeRelationshipRead])
def get_entity_relationships(
    entity_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[KnowledgeRelationship]:
    _owned_entity(db, current_user.id, entity_id)
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


@router.get("/entities/{entity_id}/traverse", response_model=KnowledgeTraversalRead)
def traverse_graph(
    entity_id: int,
    depth: int = Query(default=1, ge=1, le=3),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeTraversalRead:
    root = _owned_entity(db, current_user.id, entity_id)
    seen_entity_ids = {root.id}
    frontier = {root.id}
    relationships_by_id: dict[int, KnowledgeRelationship] = {}

    for _ in range(depth):
        if not frontier:
            break
        relationships = list(
            db.scalars(
                select(KnowledgeRelationship).where(
                    KnowledgeRelationship.owner_id == current_user.id,
                    or_(
                        KnowledgeRelationship.source_entity_id.in_(frontier),
                        KnowledgeRelationship.target_entity_id.in_(frontier),
                    ),
                )
            ).all()
        )
        next_frontier: set[int] = set()
        for relationship in relationships:
            relationships_by_id[relationship.id] = relationship
            for related_id in (relationship.source_entity_id, relationship.target_entity_id):
                if related_id not in seen_entity_ids:
                    seen_entity_ids.add(related_id)
                    next_frontier.add(related_id)
        frontier = next_frontier

    entities = list(
        db.scalars(
            select(KnowledgeEntity)
            .where(
                KnowledgeEntity.owner_id == current_user.id,
                KnowledgeEntity.id.in_(seen_entity_ids),
            )
            .order_by(KnowledgeEntity.name)
        ).all()
    )
    return KnowledgeTraversalRead(
        root_entity_id=root.id,
        depth=depth,
        entities=entities,
        relationships=list(relationships_by_id.values()),
    )
