import logging
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.gemini import LLMProviderError, generate_reply
from app.memory import build_context, get_conversation_messages, get_conversation_or_none
from app.models import Conversation, Message, utc_now
from app.prompts import SYSTEM_INSTRUCTION
from app.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationCreateRequest,
    ConversationCreated,
    ConversationListItem,
    ConversationOut,
    MessageOut,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])


@router.post(
    "/conversations",
    response_model=ConversationCreated,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation session",
)
def create_conversation(
    payload: Optional[ConversationCreateRequest] = None,
    db: Session = Depends(get_db),
) -> ConversationCreated:
    title = (payload.title.strip() if payload and payload.title and payload.title.strip() else "New Conversation")
    conversation = Conversation(
        id=str(uuid4()),
        title=title,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return ConversationCreated(
        conversation_id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
    )


@router.get(
    "/conversations",
    response_model=list[ConversationListItem],
    summary="List all available conversations",
)
def list_conversations(
    db: Session = Depends(get_db),
) -> list[ConversationListItem]:
    conversations = list(
        db.scalars(
            select(Conversation).order_by(Conversation.updated_at.desc())
        ).all()
    )

    result = []
    for conv in conversations:
        result.append(
            ConversationListItem(
                id=conv.id,
                title=conv.title,
                summary=conv.summary,
                message_count=len(conv.messages),
                created_at=conv.created_at,
                updated_at=conv.updated_at,
            )
        )
    return result


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationOut,
    summary="Retrieve conversation details and complete message history",
)
def read_conversation(
    conversation_id: str, db: Session = Depends(get_db)
) -> ConversationOut:
    conversation = get_conversation_or_none(db, conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    messages = get_conversation_messages(db, conversation.id, include_archived=True)

    return ConversationOut(
        conversation_id=conversation.id,
        title=conversation.title,
        summary=conversation.summary,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[MessageOut.model_validate(item) for item in messages],
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete conversation and associated message history",
)
def delete_conversation(
    conversation_id: str, db: Session = Depends(get_db)
) -> Response:
    conversation = get_conversation_or_none(db, conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    db.delete(conversation)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Send a message and get an AI response with memory continuity",
)
async def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ChatResponse:
    message_text = payload.message.strip()
    if not message_text:
        raise HTTPException(
            status_code=422,
            detail="Message cannot be blank or whitespace only.",
        )

    if len(message_text) > settings.max_message_chars:
        raise HTTPException(
            status_code=413,
            detail=f"Message exceeds the {settings.max_message_chars}-character limit.",
        )

    conversation = get_conversation_or_none(db, payload.conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found. Create a new conversation first.",
        )

    # Auto-generate a descriptive title from the first message if still default
    if conversation.title == "New Conversation":
        snippet = message_text.split("\n")[0][:45].strip()
        conversation.title = snippet if snippet else "New Conversation"

    # Persist the user message before calling the LLM
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=message_text,
    )
    db.add(user_message)
    conversation.updated_at = utc_now()
    db.commit()
    db.refresh(user_message)

    try:
        # Build context (performs rolling summarization if threshold reached)
        context = await build_context(db, conversation, settings=settings)
        reply = await generate_reply(context, SYSTEM_INSTRUCTION)
    except LLMProviderError as exc:
        logger.error("LLMProviderError during chat: %s (status %d)", exc.message, exc.status_code)
        # Rollback the user message so DB is not left in an inconsistent one-sided state
        try:
            db.delete(user_message)
            db.commit()
        except Exception:
            db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as exc:
        logger.exception("Unexpected error during chat processing")
        try:
            db.delete(user_message)
            db.commit()
        except Exception:
            db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while processing your message.",
        ) from exc

    # Persist the assistant's reply
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=reply,
    )
    db.add(assistant_message)
    conversation.updated_at = utc_now()
    db.commit()

    # Total messages in context includes context sent to Gemini plus the newly added assistant reply
    messages_in_context = len(context) + 1

    return ChatResponse(
        conversation_id=conversation.id,
        reply=reply,
        context_summary=conversation.summary,
        messages_in_context=messages_in_context,
    )
