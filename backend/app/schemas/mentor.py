from datetime import datetime

from pydantic import BaseModel, Field


class MentorChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    conversation_id: int | None = None
    context: dict = Field(default_factory=dict)


class EvidenceItem(BaseModel):
    label: str
    detail: str
    source_type: str = "platform_context"


class MentorRecommendation(BaseModel):
    title: str
    reason: str
    action_type: str
    action_target: str | None = None


class MentorChatResponse(BaseModel):
    conversation_id: int
    message_id: int
    intent: str
    persona: str
    answer: str
    evidence: list[EvidenceItem]
    reasoning: list[str]
    assumptions: list[str]
    confidence: str
    confidence_reason: str
    alternative_viewpoints: list[str]
    recommendations: list[MentorRecommendation]
    created_at: datetime


class MentorMessageRead(BaseModel):
    id: int
    role: str
    content: str
    intent: str | None
    persona: str | None
    response_payload: dict | None
    created_at: datetime


class MentorConversationRead(BaseModel):
    id: int
    title: str
    summary: str | None
    active_context: dict
    created_at: datetime
    updated_at: datetime


class MentorConversationDetail(MentorConversationRead):
    messages: list[MentorMessageRead]
