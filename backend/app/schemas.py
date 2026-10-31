from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

SUPPORTED_MODES = ("swift", "balanced", "deep")


class ConversationCreateRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    mode: Optional[str] = Field(default="balanced")

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: Optional[str]) -> str:
        if v is None:
            return "balanced"
        cleaned = v.strip().lower()
        if cleaned not in SUPPORTED_MODES:
            raise ValueError(f"Invalid mode '{v}'. Must be one of: {', '.join(SUPPORTED_MODES)}")
        return cleaned


class ConversationModeUpdateRequest(BaseModel):
    mode: str

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        cleaned = (v or "").strip().lower()
        if cleaned not in SUPPORTED_MODES:
            raise ValueError(f"Invalid mode '{v}'. Must be one of: {', '.join(SUPPORTED_MODES)}")
        return cleaned


class ConversationCreated(BaseModel):
    id: str
    conversation_id: str
    title: str = "New Conversation"
    mode: str = "balanced"
    created_at: datetime


class ConversationListItem(BaseModel):
    id: str
    conversation_id: str
    title: str
    mode: str = "balanced"
    summary: str
    message_count: int
    messages_count: int
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
    mode: str = Field(
        default="balanced",
        description="The intelligence mode: swift, balanced, or deep.",
    )

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        cleaned = (v or "").strip().lower()
        if cleaned not in SUPPORTED_MODES:
            raise ValueError(f"Invalid mode '{v}'. Must be one of: {', '.join(SUPPORTED_MODES)}")
        return cleaned


class ChatResponse(BaseModel):
    conversation_id: str
    id: Optional[str] = None
    reply: str
    mode: str
    model_label: str
    context_summary: str
    messages_in_context: int


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    mode: Optional[str] = None
    model_label: Optional[str] = None
    created_at: datetime


class ConversationOut(BaseModel):
    id: str
    conversation_id: str
    title: str
    mode: str = "balanced"
    summary: str
    context_summary: Optional[str] = None
    messages_in_context: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut]
