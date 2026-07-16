import hashlib
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routes.research_conclusion_export_packet import get_conclusion_export_packet
from app.db.session import get_db
from app.models.research_conclusion_defense import ResearchConclusionDefense, ResearchConclusionDefenseRevision
from app.models.user import User
from app.schemas.research_conclusion_defense_export_packet import (
    DefensePacketContent,
    DefensePacketRevision,
    ResearchConclusionDefenseExportPacket,
    ResearchConclusionDefensePacketContent,
)

router = APIRouter()
DISCLAIMER = (
    "This packet preserves user-authored conclusion and defense-review records for review and archival. "
    "Exporting does not author, grade, approve, publish, or certify the work."
)
DEFENSE_DISCLAIMER = (
    "Defense completeness only records whether the user supplied each reflection section; it does not assess truth or quality."
)


def _canonical_sha256(content: ResearchConclusionDefensePacketContent) -> str:
    payload = json.dumps(
        content.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@router.get("/projects/{project_id}", response_model=ResearchConclusionDefenseExportPacket)
def get_conclusion_defense_export_packet(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchConclusionDefenseExportPacket:
    conclusion_packet = get_conclusion_export_packet(project_id=project_id, current_user=current_user, db=db)
    defense = db.scalar(
        select(ResearchConclusionDefense).where(
            ResearchConclusionDefense.owner_id == current_user.id,
            ResearchConclusionDefense.project_id == project_id,
        )
    )

    if defense is None:
        defense_content = DefensePacketContent(status="missing", disclaimer=DEFENSE_DISCLAIMER)
    else:
        conclusion_revision_numbers = {item.revision_number for item in conclusion_packet.content.revisions}
        if defense.conclusion_revision_number is not None and defense.conclusion_revision_number not in conclusion_revision_numbers:
            raise HTTPException(status_code=409, detail="Stored defense references an invalid conclusion revision")
        conclusion_evidence_ids = set(conclusion_packet.content.evidence_ids)
        invalid_evidence = [item for item in defense.evidence_ids if item not in conclusion_evidence_ids]
        if invalid_evidence:
            raise HTTPException(
                status_code=409,
                detail={"message": "Stored defense references evidence outside the conclusion packet", "evidence_ids": invalid_evidence},
            )
        revision_records = list(
            db.scalars(
                select(ResearchConclusionDefenseRevision)
                .where(
                    ResearchConclusionDefenseRevision.defense_id == defense.id,
                    ResearchConclusionDefenseRevision.owner_id == current_user.id,
                    ResearchConclusionDefenseRevision.project_id == project_id,
                )
                .order_by(ResearchConclusionDefenseRevision.revision_number)
            ).all()
        )
        revisions = [DefensePacketRevision.model_validate(item, from_attributes=True) for item in revision_records]
        defense_content = DefensePacketContent(
            status=defense.status,
            conclusion_revision_number=defense.conclusion_revision_number,
            evidence_ids=list(defense.evidence_ids),
            evidence_coverage=defense.evidence_coverage,
            strongest_counterargument=defense.strongest_counterargument,
            known_limitations=defense.known_limitations,
            unresolved_questions=defense.unresolved_questions,
            confidence_rationale=defense.confidence_rationale,
            missing_sections=list(defense.missing_sections),
            revision_count=defense.revision_count,
            revisions=revisions,
            disclaimer=DEFENSE_DISCLAIMER,
        )

    content = ResearchConclusionDefensePacketContent(
        conclusion=conclusion_packet.content,
        defense=defense_content,
        disclaimer=DISCLAIMER,
    )
    return ResearchConclusionDefenseExportPacket(
        content_sha256=_canonical_sha256(content),
        generated_at=datetime.utcnow(),
        content=content,
    )
