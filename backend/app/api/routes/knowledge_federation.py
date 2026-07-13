from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.knowledge_federation import (
    KnowledgeFederationLink,
    KnowledgeFederationRevision,
)
from app.models.research_project import ResearchProject
from app.models.user import User
from app.schemas.knowledge_federation import (
    KnowledgeFederationLinkRead,
    KnowledgeFederationScanResult,
    KnowledgeFederationSynthesis,
    KnowledgeFederationUpdate,
)
from app.services.knowledge_federation_service import list_links, scan_project

router = APIRouter()


def _owned_project(db: Session, owner_id: int, project_id: int) -> ResearchProject:
    project = db.scalar(
        select(ResearchProject).where(
            ResearchProject.id == project_id,
            ResearchProject.owner_id == owner_id,
        )
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Research project not found")
    return project


def _owned_link(db: Session, owner_id: int, link_id: int) -> KnowledgeFederationLink:
    link = db.scalar(
        select(KnowledgeFederationLink).where(
            KnowledgeFederationLink.id == link_id,
            KnowledgeFederationLink.owner_id == owner_id,
        )
    )
    if link is None:
        raise HTTPException(status_code=404, detail="Knowledge federation link not found")
    return link


def _revisions(db: Session, link_id: int) -> list[KnowledgeFederationRevision]:
    return list(
        db.scalars(
            select(KnowledgeFederationRevision)
            .where(KnowledgeFederationRevision.link_id == link_id)
            .order_by(KnowledgeFederationRevision.revision_number)
        ).all()
    )


def _read(db: Session, link: KnowledgeFederationLink) -> KnowledgeFederationLinkRead:
    return KnowledgeFederationLinkRead(
        **{
            column.name: getattr(link, column.name)
            for column in KnowledgeFederationLink.__table__.columns
        },
        revisions=_revisions(db, link.id),
    )


@router.post(
    "/projects/{project_id}/scan",
    response_model=KnowledgeFederationScanResult,
)
def scan_project_federation(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeFederationScanResult:
    _owned_project(db, current_user.id, project_id)
    links, created, reused = scan_project(db, current_user.id, project_id)
    return KnowledgeFederationScanResult(
        links=[_read(db, link) for link in links],
        created_count=created,
        reused_count=reused,
    )


@router.get("", response_model=list[KnowledgeFederationLinkRead])
def get_federation_links(
    project_id: int | None = Query(default=None),
    link_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[KnowledgeFederationLinkRead]:
    links = list_links(
        db,
        current_user.id,
        project_id=project_id,
        link_type=link_type,
        status=status,
    )
    return [_read(db, link) for link in links]


@router.get("/synthesis", response_model=KnowledgeFederationSynthesis)
def synthesize_federation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeFederationSynthesis:
    links = list_links(db, current_user.id)
    grouped = {
        link_type: []
        for link_type in (
            "duplicate",
            "supporting",
            "contradicting",
            "related",
            "superseding",
        )
    }
    for link in links:
        grouped.setdefault(link.link_type, []).append(_read(db, link))
    return KnowledgeFederationSynthesis(
        total_links=len(links),
        duplicates=grouped["duplicate"],
        supporting=grouped["supporting"],
        contradicting=grouped["contradicting"],
        related=grouped["related"],
        superseding=grouped["superseding"],
    )


@router.get(
    "/projects/{project_id}/related",
    response_model=list[KnowledgeFederationLinkRead],
)
def get_related_project_links(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[KnowledgeFederationLinkRead]:
    _owned_project(db, current_user.id, project_id)
    return [
        _read(db, link)
        for link in list_links(db, current_user.id, project_id=project_id)
    ]


@router.get("/{link_id}", response_model=KnowledgeFederationLinkRead)
def get_federation_link(
    link_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeFederationLinkRead:
    return _read(db, _owned_link(db, current_user.id, link_id))


@router.patch("/{link_id}", response_model=KnowledgeFederationLinkRead)
def revise_federation_link(
    link_id: int,
    payload: KnowledgeFederationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeFederationLinkRead:
    link = _owned_link(db, current_user.id, link_id)
    changed = False
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is not None and getattr(link, key) != value:
            setattr(link, key, value)
            changed = True
    if changed:
        link.revision_number += 1
        db.add(
            KnowledgeFederationRevision(
                link_id=link.id,
                revision_number=link.revision_number,
                link_type=link.link_type,
                score=link.score,
                score_components=link.score_components,
                provenance=link.provenance,
                status=link.status,
            )
        )
        db.commit()
        db.refresh(link)
    return _read(db, link)
