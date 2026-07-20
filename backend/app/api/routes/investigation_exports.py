from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routes.investigation_reports import quality_assessment, validation_report
from app.db.session import get_db
from app.models.user import User
from app.schemas.investigation_report import InvestigationEvidencePacket

router = APIRouter()


@router.get("/{investigation_id}/evidence-packet", response_model=InvestigationEvidencePacket)
def read_evidence_packet(
    investigation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvestigationEvidencePacket:
    report = validation_report(investigation_id, current_user, db)
    assessment = quality_assessment(investigation_id, current_user, db)
    return InvestigationEvidencePacket(
        investigation_id=report.investigation_id,
        validation_report=report,
        quality_assessment=assessment,
        generated_from_stored_state_at=max(
            report.generated_from_stored_state_at,
            assessment.generated_from_stored_state_at,
        ),
    )
