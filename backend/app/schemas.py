from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreateRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)


class ConversationCreated(BaseModel):
    conversation_id: str
    title: str = "New Conversation"
    created_at: datetime


class ConversationListItem(BaseModel):
    id: str
    title: str
    summary: str
    message_count: int
    created_at: datetime
    updated_at: datetime


class ChatRequest(BaseModel):
    conversation_id: str = Field(
        ...,
        min_length=36,
        max_length=36,
        description="The UUID of the conversation session.",
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=8000,
        description="The user's message text.",
    )


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
    context_summary: str
    messages_in_context: int


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    created_at: datetime


class ConversationOut(BaseModel):
    conversation_id: str
    title: str
    summary: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut]
