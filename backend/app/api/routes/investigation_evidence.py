from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.investigation import Investigation
from app.models.investigation_evidence import ClaimEvidence, InvestigationClaim
from app.models.user import User
from app.schemas.investigation_evidence import (
    ClaimCreate,
    ClaimRead,
    ClaimUpdate,
    EvidenceCreate,
    EvidenceRead,
    EvidenceUpdate,
)

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


def _owned_claim(db: Session, user_id: int, claim_id: int) -> InvestigationClaim:
    claim = db.scalar(
        select(InvestigationClaim)
        .join(Investigation, Investigation.id == InvestigationClaim.investigation_id)
        .where(InvestigationClaim.id == claim_id, Investigation.owner_id == user_id)
    )
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim


def _owned_evidence(db: Session, user_id: int, evidence_id: int) -> ClaimEvidence:
    evidence = db.scalar(
        select(ClaimEvidence)
        .join(InvestigationClaim, InvestigationClaim.id == ClaimEvidence.claim_id)
        .join(Investigation, Investigation.id == InvestigationClaim.investigation_id)
        .where(ClaimEvidence.id == evidence_id, Investigation.owner_id == user_id)
    )
    if evidence is None:
        raise HTTPException(status_code=404, detail="Evidence not found")
    return evidence


@router.post(
    "/{investigation_id}/claims",
    response_model=ClaimRead,
    status_code=status.HTTP_201_CREATED,
)
def create_claim(
    investigation_id: int,
    payload: ClaimCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvestigationClaim:
    _owned_investigation(db, current_user.id, investigation_id)
    claim = InvestigationClaim(investigation_id=investigation_id, statement=payload.statement)
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim


@router.get("/{investigation_id}/claims", response_model=list[ClaimRead])
def list_claims(
    investigation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[InvestigationClaim]:
    _owned_investigation(db, current_user.id, investigation_id)
    return list(
        db.scalars(
            select(InvestigationClaim)
            .where(InvestigationClaim.investigation_id == investigation_id)
            .order_by(InvestigationClaim.updated_at.desc(), InvestigationClaim.id.desc())
        ).all()
    )


@router.patch("/claims/{claim_id}", response_model=ClaimRead)
def update_claim(
    claim_id: int,
    payload: ClaimUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvestigationClaim:
    claim = _owned_claim(db, current_user.id, claim_id)
    claim.statement = payload.statement
    db.commit()
    db.refresh(claim)
    return claim


@router.delete("/claims/{claim_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_claim(
    claim_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    claim = _owned_claim(db, current_user.id, claim_id)
    db.delete(claim)
    db.commit()


@router.post(
    "/claims/{claim_id}/evidence",
    response_model=EvidenceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_evidence(
    claim_id: int,
    payload: EvidenceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClaimEvidence:
    _owned_claim(db, current_user.id, claim_id)
    evidence = ClaimEvidence(claim_id=claim_id, **payload.model_dump())
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence


@router.get("/claims/{claim_id}/evidence", response_model=list[EvidenceRead])
def list_evidence(
    claim_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ClaimEvidence]:
    _owned_claim(db, current_user.id, claim_id)
    return list(
        db.scalars(
            select(ClaimEvidence)
            .where(ClaimEvidence.claim_id == claim_id)
            .order_by(ClaimEvidence.updated_at.desc(), ClaimEvidence.id.desc())
        ).all()
    )


@router.patch("/evidence/{evidence_id}", response_model=EvidenceRead)
def update_evidence(
    evidence_id: int,
    payload: EvidenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClaimEvidence:
    evidence = _owned_evidence(db, current_user.id, evidence_id)
    for field_name, value in payload.model_dump().items():
        setattr(evidence, field_name, value)
    db.commit()
    db.refresh(evidence)
    return evidence


@router.delete("/evidence/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_evidence(
    evidence_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    evidence = _owned_evidence(db, current_user.id, evidence_id)
    db.delete(evidence)
    db.commit()
