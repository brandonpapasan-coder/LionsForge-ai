from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.mentor import MentorConversation, MentorMessage
from app.models.research_project import ResearchProject
from app.models.research_session import ResearchSession
from app.models.user import User
from app.schemas.mentor import (
    MentorChatRequest,
    MentorChatResponse,
    MentorConversationDetail,
    MentorConversationRead,
)
from app.services.mentor import MentorOrchestrator

router = APIRouter()
orchestrator = MentorOrchestrator()


def _owned_conversation(db: Session, user_id: int, conversation_id: int) -> MentorConversation:
    conversation = db.scalar(
        select(MentorConversation).where(
            MentorConversation.id == conversation_id,
            MentorConversation.user_id == user_id,
        )
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Mentor conversation not found")
    return conversation


def _context_id(context: dict, key: str) -> int | None:
    raw_value = context.get(key)
    if raw_value in (None, ""):
        return None
    try:
        return int(raw_value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid {key}") from exc


def _resolve_research_context(db: Session, user_id: int, context: dict) -> dict:
    resolved = dict(context)
    project_id = _context_id(context, "research_project_id")
    session_id = _context_id(context, "research_session_id")

    project: ResearchProject | None = None
    if project_id is not None:
        project = db.scalar(
            select(ResearchProject).where(
                ResearchProject.id == project_id,
                ResearchProject.owner_id == user_id,
            )
        )
        if project is None:
            raise HTTPException(status_code=404, detail="Research project not found")
        resolved["research_project"] = {
            "id": project.id,
            "title": project.title,
            "description": project.description,
            "objective": project.objective,
            "status": project.status,
            "context": project.context or {},
        }

    if session_id is not None:
        session = db.scalar(
            select(ResearchSession)
            .join(ResearchProject, ResearchSession.project_id == ResearchProject.id)
            .where(
                ResearchSession.id == session_id,
                ResearchProject.owner_id == user_id,
            )
        )
        if session is None:
            raise HTTPException(status_code=404, detail="Research session not found")
        if project is not None and session.project_id != project.id:
            raise HTTPException(status_code=400, detail="Research session does not belong to project")
        resolved["research_session"] = {
            "id": session.id,
            "project_id": session.project_id,
            "title": session.title,
            "objective": session.objective,
            "summary": session.summary,
            "status": session.status,
            "context": session.context or {},
        }

    return resolved


@router.post("/chat", response_model=MentorChatResponse, status_code=status.HTTP_201_CREATED)
def chat(
    payload: MentorChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MentorChatResponse:
    resolved_context = _resolve_research_context(db, current_user.id, payload.context)

    if payload.conversation_id is None:
        conversation = MentorConversation(
            user_id=current_user.id,
            title=payload.message.strip()[:157] or "New mentor conversation",
            active_context=resolved_context,
        )
        db.add(conversation)
        db.flush()
    else:
        conversation = _owned_conversation(db, current_user.id, payload.conversation_id)
        conversation.active_context = {**(conversation.active_context or {}), **resolved_context}

    db.add(
        MentorMessage(
            conversation_id=conversation.id,
            role="user",
            content=payload.message.strip(),
        )
    )

    response_payload = orchestrator.compose(payload.message, conversation.active_context or {})
    assistant_message = MentorMessage(
        conversation_id=conversation.id,
        role="assistant",
        content=response_payload["answer"],
        intent=response_payload["intent"],
        persona=response_payload["persona"],
        response_payload=response_payload,
    )
    db.add(assistant_message)
    conversation.summary = f"{response_payload['intent']} discussion guided by {response_payload['persona']}"
    db.commit()
    db.refresh(assistant_message)

    return MentorChatResponse(
        conversation_id=conversation.id,
        message_id=assistant_message.id,
        created_at=assistant_message.created_at,
        **response_payload,
    )


@router.get("/conversations", response_model=list[MentorConversationRead])
def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MentorConversation]:
    return list(
        db.scalars(
            select(MentorConversation)
            .where(MentorConversation.user_id == current_user.id)
            .order_by(desc(MentorConversation.updated_at))
        ).all()
    )


@router.get("/conversations/{conversation_id}", response_model=MentorConversationDetail)
def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MentorConversation:
    conversation = db.scalar(
        select(MentorConversation)
        .options(selectinload(MentorConversation.messages))
        .where(
            MentorConversation.id == conversation_id,
            MentorConversation.user_id == current_user.id,
        )
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Mentor conversation not found")
    conversation.messages.sort(key=lambda message: (message.created_at, message.id))
    return conversation
