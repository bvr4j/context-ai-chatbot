import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_five_turn_memory_retention(client: AsyncClient, mock_gemini):
    """Simulate a full 5-turn multi-turn conversation verifying state retention and message ordering."""
    # Step 1: Create conversation
    res = await client.post("/api/conversations", json={"title": "Jordan's Architecture Session"})
    assert res.status_code == 201
    convo_id = res.json()["conversation_id"]

    scripted_turns = [
        (
            "Hello! My name is Jordan and I am a backend engineer.",
            "Hello Jordan! Nice to meet you. How can I assist you with backend engineering today?",
        ),
        (
            "I am designing a real-time event streaming pipeline using Apache Kafka.",
            "Apache Kafka is great for high-throughput distributed event streaming. Are you using schema registries?",
        ),
        (
            "We are using Python with FastAPI and SQLAlchemy.",
            "FastAPI with SQLAlchemy is a productive stack. You can run Kafka consumers asynchronously.",
        ),
        (
            "What is my name and what streaming tool did I say we are using?",
            "Your name is Jordan, and you are using Apache Kafka for real-time event streaming.",
        ),
        (
            "What database ORM did I specify?",
            "You mentioned you are using SQLAlchemy alongside FastAPI.",
        ),
    ]

    for turn_index, (user_msg, assistant_reply) in enumerate(scripted_turns, start=1):
        mock_gemini["generate_reply"].return_value = assistant_reply

        response = await client.post(
            "/api/chat",
            json={"conversation_id": convo_id, "message": user_msg},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == convo_id
        assert data["reply"] == assistant_reply
        assert data["messages_in_context"] >= 2

    # Step 2: Retrieve full history and inspect
    history_res = await client.get(f"/api/conversations/{convo_id}")
    assert history_res.status_code == 200
    history = history_res.json()

    messages = history["messages"]
    assert len(messages) == 10  # 5 user messages + 5 assistant messages

    # Check chronological order and role alternation
    for i, (user_msg, assistant_reply) in enumerate(scripted_turns):
        user_turn = messages[i * 2]
        assistant_turn = messages[i * 2 + 1]

        assert user_turn["role"] == "user"
        assert user_turn["content"] == user_msg
        assert assistant_turn["role"] == "assistant"
        assert assistant_turn["content"] == assistant_reply
