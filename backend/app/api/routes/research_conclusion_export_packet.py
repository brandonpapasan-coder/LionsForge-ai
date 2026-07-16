import hashlib
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routes.research_conclusion_readiness import get_conclusion_readiness
from app.db.session import get_db
from app.models.evidence import EvidenceRecord
from app.models.research_conclusion import ResearchConclusion, ResearchConclusionRevision
from app.models.research_project import ResearchProject
from app.models.user import User
from app.schemas.research_conclusion_export_packet import (
    ConclusionPacketEvidence,
    ConclusionPacketReadiness,
    ConclusionPacketRevision,
    ResearchConclusionExportPacket,
    ResearchConclusionPacketContent,
)

router = APIRouter()
DISCLAIMER = (
    "This packet preserves a user-authored conclusion and its research trail for review and archival. "
    "Exporting does not publish, approve, certify, or independently author the conclusion."
)


def _canonical_sha256(content: ResearchConclusionPacketContent) -> str:
    payload = json.dumps(
        content.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@router.get("/projects/{project_id}", response_model=ResearchConclusionExportPacket)
def get_conclusion_export_packet(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchConclusionExportPacket:
    project = db.scalar(
        select(ResearchProject).where(
            ResearchProject.id == project_id,
            ResearchProject.owner_id == current_user.id,
        )
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Research project not found")

    conclusion = db.scalar(
        select(ResearchConclusion).where(
            ResearchConclusion.owner_id == current_user.id,
            ResearchConclusion.project_id == project_id,
        )
    )
    evidence_ids = list(conclusion.evidence_ids) if conclusion is not None else []
    evidence = []
    if evidence_ids:
        records = list(
            db.scalars(
                select(EvidenceRecord).where(
                    EvidenceRecord.owner_id == current_user.id,
                    EvidenceRecord.project_id == project_id,
                    EvidenceRecord.id.in_(evidence_ids),
                )
            ).all()
        )
        by_id = {item.id: item for item in records}
        missing = [evidence_id for evidence_id in evidence_ids if evidence_id not in by_id]
        if missing:
            raise HTTPException(
                status_code=409,
                detail={"message": "Stored conclusion contains invalid evidence references", "evidence_ids": missing},
            )
        evidence = [ConclusionPacketEvidence.model_validate(by_id[evidence_id], from_attributes=True) for evidence_id in evidence_ids]

    revisions = []
    if conclusion is not None:
        revision_records = list(
            db.scalars(
                select(ResearchConclusionRevision)
                .where(
                    ResearchConclusionRevision.conclusion_id == conclusion.id,
                    ResearchConclusionRevision.owner_id == current_user.id,
                    ResearchConclusionRevision.project_id == project_id,
                )
                .order_by(ResearchConclusionRevision.revision_number)
            ).all()
        )
        revisions = [ConclusionPacketRevision.model_validate(item, from_attributes=True) for item in revision_records]

    readiness = get_conclusion_readiness(project_id=project_id, current_user=current_user, db=db)
    content = ResearchConclusionPacketContent(
        project_id=project.id,
        project_title=project.title,
        conclusion_status=conclusion.status if conclusion is not None else "missing",
        conclusion_text=conclusion.conclusion_text if conclusion is not None else "",
        evidence_ids=evidence_ids,
        evidence=evidence,
        revisions=revisions,
        readiness=ConclusionPacketReadiness.model_validate(readiness.model_dump()),
        disclaimer=DISCLAIMER,
    )
    return ResearchConclusionExportPacket(
        content_sha256=_canonical_sha256(content),
        generated_at=datetime.utcnow(),
        content=content,
    )
