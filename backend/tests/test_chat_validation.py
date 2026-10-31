import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_chat_empty_message(client: AsyncClient):
    res = await client.post("/api/conversations")
    convo_id = res.json()["conversation_id"]

    # Blank string
    response = await client.post(
        "/api/chat", json={"conversation_id": convo_id, "message": "   "}
    )
    assert response.status_code == 422
    assert "blank" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_chat_invalid_conversation_id_length(client: AsyncClient):
    response = await client.post(
        "/api/chat", json={"conversation_id": "short-id", "message": "Hello"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_nonexistent_conversation(client: AsyncClient):
    fake_id = "11111111-2222-3333-4444-555555555555"
    response = await client.post(
        "/api/chat", json={"conversation_id": fake_id, "message": "Hello"}
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_chat_oversized_message(client: AsyncClient):
    res = await client.post("/api/conversations")
    convo_id = res.json()["conversation_id"]

    # max_message_chars in test_settings is 500
    oversized = "A" * 600
    response = await client.post(
        "/api/chat", json={"conversation_id": convo_id, "message": oversized}
    )
    assert response.status_code == 413
    assert "limit" in response.json()["detail"].lower()
