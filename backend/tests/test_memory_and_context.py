from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.memory import _find_balanced_turn_split, build_context
from app.models import Conversation, Message


@pytest.mark.asyncio
async def test_independent_conversation_histories(client: AsyncClient, mock_gemini):
    """Ensure two conversations do not share messages, summaries, or context."""
    res1 = await client.post("/api/conversations", json={"title": "Session Alpha"})
    res2 = await client.post("/api/conversations", json={"title": "Session Beta"})
    id1 = res1.json()["conversation_id"]
    id2 = res2.json()["conversation_id"]

    mock_gemini["generate_reply"].side_effect = ["Reply for Alpha", "Reply for Beta"]

    await client.post("/api/chat", json={"conversation_id": id1, "message": "Message for Alpha"})
    await client.post("/api/chat", json={"conversation_id": id2, "message": "Message for Beta"})

    # Check history of Session Alpha
    hist1 = (await client.get(f"/api/conversations/{id1}")).json()
    assert len(hist1["messages"]) == 2
    assert hist1["messages"][0]["content"] == "Message for Alpha"
    assert hist1["messages"][1]["content"] == "Reply for Alpha"

    # Check history of Session Beta
    hist2 = (await client.get(f"/api/conversations/{id2}")).json()
    assert len(hist2["messages"]) == 2
    assert hist2["messages"][0]["content"] == "Message for Beta"
    assert hist2["messages"][1]["content"] == "Reply for Beta"


@pytest.mark.asyncio
async def test_balanced_turn_split_helper():
    """Verify _find_balanced_turn_split never splits user/assistant pairs."""
    # Create mock messages
    m1 = Message(id=1, conversation_id="c1", role="user", content="u1")
    m2 = Message(id=2, conversation_id="c1", role="assistant", content="a1")
    m3 = Message(id=3, conversation_id="c1", role="user", content="u2")
    m4 = Message(id=4, conversation_id="c1", role="assistant", content="a2")
    m5 = Message(id=5, conversation_id="c1", role="user", content="u3")

    # Overflow target 3 with 5 messages
    split = _find_balanced_turn_split([m1, m2, m3, m4, m5], 3)
    # Target 3 is odd; it should round down to 2 so m1 and m2 are paired
    assert split == 2

    # Overflow target 4 with 5 messages
    split = _find_balanced_turn_split([m1, m2, m3, m4, m5], 4)
    # Target 4 gives m1, m2, m3, m4 (2 complete pairs)
    assert split == 4

    # Overflow target 1 with 2 messages
    split = _find_balanced_turn_split([m1, m2], 1)
    assert split == 0  # Cannot split 1 without breaking the pair


@pytest.mark.asyncio
async def test_rolling_summarization_trigger(client: AsyncClient, mock_gemini, db_session: Session):
    """Verify that when message count exceeds trigger, older turns are summarized into SQLite."""
    res = await client.post("/api/conversations", json={"title": "Summarization Test"})
    convo_id = res.json()["conversation_id"]

    mock_gemini["generate_reply"].return_value = "Standard assistant answer."
    mock_gemini["summarize_text"].return_value = "User is building a high-scale microservices system."

    # Test settings: max_context_messages=4, summary_trigger_messages=6
    # Turn 1: 2 messages
    await client.post("/api/chat", json={"conversation_id": convo_id, "message": "Turn 1"})
    # Turn 2: 4 messages
    await client.post("/api/chat", json={"conversation_id": convo_id, "message": "Turn 2"})
    # Turn 3: 6 messages
    await client.post("/api/chat", json={"conversation_id": convo_id, "message": "Turn 3"})

    conv_before = db_session.get(Conversation, convo_id)
    assert conv_before.summary == ""

    # Turn 4: user message is 7th message, triggering summary!
    chat_res4 = await client.post("/api/chat", json={"conversation_id": convo_id, "message": "Turn 4"})
    assert chat_res4.status_code == 200

    db_session.expire_all()
    conv_after = db_session.get(Conversation, convo_id)
    # Verify summary is now persisted in SQLite
    assert conv_after.summary == "User is building a high-scale microservices system."
    assert chat_res4.json()["context_summary"] == "User is building a high-scale microservices system."

    # Verify that full history is preserved when retrieving the conversation
    history_res = await client.get(f"/api/conversations/{convo_id}")
    history_data = history_res.json()
    assert len(history_data["messages"]) == 8  # All 4 turns (8 messages) are retained!
    assert history_data["summary"] == "User is building a high-scale microservices system."


@pytest.mark.asyncio
async def test_summary_inclusion_in_openai_context(db_session: Session):
    """Verify that the stored summary is formatted with non-instructional delimiters for OpenAI."""
    conv = Conversation(
        id="test-summary-context-uuid-111111111111",
        title="Context Check",
        summary="User preferred dark theme and Python 3.12.",
    )
    db_session.add(conv)
    m1 = Message(conversation_id=conv.id, role="user", content="What did I prefer?")
    db_session.add(m1)
    db_session.commit()

    context = await build_context(db_session, conv)

    # First content block must be the memory summary
    assert len(context) >= 3
    summary_text = context[0]["content"]
    assert "[CONVERSATION MEMORY SUMMARY" in summary_text
    assert "User preferred dark theme and Python 3.12." in summary_text
    assert context[0]["role"] == "user"

    # Second content block must be assistant acknowledgment
    assert context[1]["role"] == "assistant"
    assert "background summary" in context[1]["content"].lower()

    # Third content block is the actual user message
    assert context[2]["role"] == "user"
    assert context[2]["content"] == "What did I prefer?"
