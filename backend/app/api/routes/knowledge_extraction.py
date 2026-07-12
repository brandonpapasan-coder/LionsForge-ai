from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.knowledge_extraction import KnowledgeExtractionRequest, KnowledgeExtractionResponse
from app.services.knowledge_extraction_service import extract_and_optionally_persist

router = APIRouter()


@router.post("/extract", response_model=KnowledgeExtractionResponse)
def extract_knowledge(
    payload: KnowledgeExtractionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeExtractionResponse:
    return extract_and_optionally_persist(db, current_user.id, payload)
