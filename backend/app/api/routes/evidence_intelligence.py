from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.evidence import EvidenceRecord
from app.models.knowledge_graph import KnowledgeEntity
from app.models.research_project import ResearchProject
from app.models.user import User
from app.schemas.evidence_intelligence import EvidenceConflictGroup, EvidenceCreate, EvidenceRead, EvidenceReview
from app.services.evidence_intelligence_service import build_evidence_record, conflict_groups, find_duplicate

router = APIRouter()


def _owned_evidence(db: Session, owner_id: int, evidence_id: int) -> EvidenceRecord:
    item = db.scalar(
        select(EvidenceRecord).where(EvidenceRecord.id == evidence_id, EvidenceRecord.owner_id == owner_id)
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return item


def _validate_links(db: Session, owner_id: int, project_id: int | None, entity_id: int | None) -> None:
    if project_id is not None and db.scalar(
        select(ResearchProject.id).where(ResearchProject.id == project_id, ResearchProject.owner_id == owner_id)
    ) is None:
        raise HTTPException(status_code=404, detail="Research project not found")
    if entity_id is not None and db.scalar(
        select(KnowledgeEntity.id).where(KnowledgeEntity.id == entity_id, KnowledgeEntity.owner_id == owner_id)
    ) is None:
        raise HTTPException(status_code=404, detail="Knowledge entity not found")


@router.post("", response_model=EvidenceRead, status_code=status.HTTP_201_CREATED)
def create_evidence(
    payload: EvidenceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EvidenceRecord:
    data = payload.model_dump()
    _validate_links(db, current_user.id, data.get("project_id"), data.get("entity_id"))
    item = build_evidence_record(current_user.id, data)
    duplicate = find_duplicate(db, current_user.id, item.fingerprint)
    if duplicate is not None:
        raise HTTPException(status_code=409, detail={"message": "Duplicate evidence", "evidence_id": duplicate.id})
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=list[EvidenceRead])
def list_evidence(
    project_id: int | None = None,
    validation_status: str | None = Query(default=None, pattern="^(unverified|approved|rejected|needs_review)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[EvidenceRecord]:
    statement = select(EvidenceRecord).where(EvidenceRecord.owner_id == current_user.id)
    if project_id is not None:
        statement = statement.where(EvidenceRecord.project_id == project_id)
    if validation_status is not None:
        statement = statement.where(EvidenceRecord.validation_status == validation_status)
    return list(db.scalars(statement.order_by(desc(EvidenceRecord.created_at))).all())


@router.get("/{evidence_id}", response_model=EvidenceRead)
def get_evidence(
    evidence_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EvidenceRecord:
    return _owned_evidence(db, current_user.id, evidence_id)


@router.patch("/{evidence_id}/review", response_model=EvidenceRead)
def review_evidence(
    evidence_id: int,
    payload: EvidenceReview,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EvidenceRecord:
    item = _owned_evidence(db, current_user.id, evidence_id)
    item.validation_status = payload.validation_status
    item.reviewer_notes = payload.reviewer_notes
    db.commit()
    db.refresh(item)
    return item


@router.get("/analysis/conflicts", response_model=list[EvidenceConflictGroup])
def list_conflicts(
    project_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[EvidenceConflictGroup]:
    groups = conflict_groups(db, current_user.id, project_id)
    return [
        EvidenceConflictGroup(
            contradiction_key=key,
            supporting=[item for item in records if item.stance == "supports"],
            contradicting=[item for item in records if item.stance == "contradicts"],
            neutral=[item for item in records if item.stance == "neutral"],
        )
        for key, records in groups.items()
    ]
