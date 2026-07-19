from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.investigation import Investigation
from app.models.user import User
from app.schemas.investigation import InvestigationCreate, InvestigationRead, InvestigationUpdate

router = APIRouter()


def _owned_investigation(db: Session, user_id: int, investigation_id: int) -> Investigation:
    investigation = db.scalar(
        select(Investigation).where(
            Investigation.id == investigation_id,
            Investigation.owner_id == user_id,
        )
    )
    if investigation is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return investigation


@router.post("", response_model=InvestigationRead, status_code=status.HTTP_201_CREATED)
def create_investigation(
    payload: InvestigationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Investigation:
    investigation = Investigation(
        owner_id=current_user.id,
        title=payload.title,
        research_question=payload.research_question,
    )
    db.add(investigation)
    db.commit()
    db.refresh(investigation)
    return investigation


@router.get("", response_model=list[InvestigationRead])
def list_investigations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Investigation]:
    return list(
        db.scalars(
            select(Investigation)
            .where(Investigation.owner_id == current_user.id)
            .order_by(Investigation.updated_at.desc(), Investigation.id.desc())
        ).all()
    )


@router.get("/{investigation_id}", response_model=InvestigationRead)
def read_investigation(
    investigation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Investigation:
    return _owned_investigation(db, current_user.id, investigation_id)


@router.patch("/{investigation_id}", response_model=InvestigationRead)
def update_investigation(
    investigation_id: int,
    payload: InvestigationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Investigation:
    investigation = _owned_investigation(db, current_user.id, investigation_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="At least one field must be updated")
    for field_name, value in changes.items():
        setattr(investigation, field_name, value)
    db.commit()
    db.refresh(investigation)
    return investigation
