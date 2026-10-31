from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.gemini import LLMProviderError
from app.models import Conversation, Message


@pytest.mark.asyncio
async def test_chat_successful_turn(client: AsyncClient, mock_gemini, db_session: Session):
    res = await client.post("/api/conversations")
    convo_id = res.json()["conversation_id"]

    mock_gemini["generate_reply"].return_value = "Hello! I am ContextAI."

    chat_res = await client.post(
        "/api/chat", json={"conversation_id": convo_id, "message": "Hi there!"}
    )
    assert chat_res.status_code == 200
    data = chat_res.json()
    assert data["conversation_id"] == convo_id
    assert data["reply"] == "Hello! I am ContextAI."
    assert data["messages_in_context"] == 2

    # Verify messages in DB
    messages = list(
        db_session.scalars(
            select(Message).where(Message.conversation_id == convo_id).order_by(Message.id.asc())
        ).all()
    )
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "Hi there!"
    assert messages[1].role == "assistant"
    assert messages[1].content == "Hello! I am ContextAI."


@pytest.mark.asyncio
async def test_chat_auto_titling(client: AsyncClient, mock_gemini, db_session: Session):
    res = await client.post("/api/conversations")
    convo_id = res.json()["conversation_id"]

    chat_res = await client.post(
        "/api/chat", json={"conversation_id": convo_id, "message": "Explain quantum computing briefly"}
    )
    assert chat_res.status_code == 200

    conv = db_session.get(Conversation, convo_id)
    assert conv is not None
    assert "Explain quantum" in conv.title


@pytest.mark.asyncio
async def test_chat_llm_provider_error_handling(client: AsyncClient, db_session: Session):
    res = await client.post("/api/conversations")
    convo_id = res.json()["conversation_id"]

    with patch("app.routes.chat.generate_reply", new_callable=AsyncMock) as mock_fail:
        mock_fail.side_effect = LLMProviderError("Upstream rate limit reached.", status_code=429)

        chat_res = await client.post(
            "/api/chat", json={"conversation_id": convo_id, "message": "Will this fail?"}
        )
        assert chat_res.status_code == 429
        assert "rate limit" in chat_res.json()["detail"].lower()

    # Verify the user message was cleaned up (no orphaned user message left in DB)
    messages = list(
        db_session.scalars(select(Message).where(Message.conversation_id == convo_id)).all()
    )
    assert len(messages) == 0


@pytest.mark.asyncio
async def test_chat_timeout_handling(client: AsyncClient, db_session: Session):
    res = await client.post("/api/conversations")
    convo_id = res.json()["conversation_id"]

    with patch("app.routes.chat.generate_reply", new_callable=AsyncMock) as mock_fail:
        mock_fail.side_effect = LLMProviderError("The AI provider timed out.", status_code=504)

        chat_res = await client.post(
            "/api/chat", json={"conversation_id": convo_id, "message": "Slow request"}
        )
        assert chat_res.status_code == 504
        assert "timed out" in chat_res.json()["detail"].lower()

    # Ensure clean database state
    messages = list(
        db_session.scalars(select(Message).where(Message.conversation_id == convo_id)).all()
    )
    assert len(messages) == 0
