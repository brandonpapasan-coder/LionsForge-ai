from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.mentor import MentorConversation, MentorMessage
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


@router.post("/chat", response_model=MentorChatResponse, status_code=status.HTTP_201_CREATED)
def chat(
    payload: MentorChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MentorChatResponse:
    if payload.conversation_id is None:
        conversation = MentorConversation(
            user_id=current_user.id,
            title=payload.message.strip()[:157] or "New mentor conversation",
            active_context=payload.context,
        )
        db.add(conversation)
        db.flush()
    else:
        conversation = _owned_conversation(db, current_user.id, payload.conversation_id)
        conversation.active_context = {**(conversation.active_context or {}), **payload.context}

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
