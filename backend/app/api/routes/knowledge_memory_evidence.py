from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.evidence import EvidenceRecord
from app.models.knowledge_memory import KnowledgeMemory
from app.models.user import User
from app.schemas.knowledge_memory import KnowledgeMemoryEvidenceTrace

router = APIRouter()


@router.get("/{memory_id}/evidence", response_model=KnowledgeMemoryEvidenceTrace)
def get_knowledge_memory_evidence(
    memory_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeMemoryEvidenceTrace:
    memory = db.scalar(
        select(KnowledgeMemory).where(
            KnowledgeMemory.id == memory_id,
            KnowledgeMemory.owner_id == current_user.id,
        )
    )
    if memory is None:
        raise HTTPException(status_code=404, detail="Knowledge memory not found")

    requested_ids = list(dict.fromkeys(memory.source_evidence_ids))
    if not requested_ids:
        return KnowledgeMemoryEvidenceTrace(
            memory_id=memory.id,
            requested_evidence_ids=[],
            evidence=[],
            unavailable_evidence_ids=[],
        )

    records = list(
        db.scalars(
            select(EvidenceRecord).where(
                EvidenceRecord.id.in_(requested_ids),
                EvidenceRecord.owner_id == current_user.id,
            )
        ).all()
    )
    records_by_id = {record.id: record for record in records}
    ordered_records = [records_by_id[evidence_id] for evidence_id in requested_ids if evidence_id in records_by_id]
    unavailable_ids = [evidence_id for evidence_id in requested_ids if evidence_id not in records_by_id]

    return KnowledgeMemoryEvidenceTrace(
        memory_id=memory.id,
        requested_evidence_ids=requested_ids,
        evidence=ordered_records,
        unavailable_evidence_ids=unavailable_ids,
    )
