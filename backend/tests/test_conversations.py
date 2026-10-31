import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_conversation_default(client: AsyncClient):
    response = await client.post("/api/conversations")
    assert response.status_code == 201
    data = response.json()
    assert "conversation_id" in data
    assert "id" in data
    assert data["id"] == data["conversation_id"]
    assert "created_at" in data
    assert data["title"] == "New Conversation"
    assert data["mode"] == "balanced"
    assert len(data["conversation_id"]) == 36


@pytest.mark.asyncio
async def test_create_conversation_custom_title(client: AsyncClient):
    response = await client.post("/api/conversations", json={"title": "Custom Project Chat"})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Custom Project Chat"


@pytest.mark.asyncio
async def test_list_conversations(client: AsyncClient):
    # Create two conversations
    res1 = await client.post("/api/conversations", json={"title": "Chat 1"})
    res2 = await client.post("/api/conversations", json={"title": "Chat 2"})
    assert res1.status_code == 201
    assert res2.status_code == 201

    list_res = await client.get("/api/conversations")
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) >= 2
    ids = [item["id"] for item in items]
    assert res1.json()["conversation_id"] in ids
    assert res2.json()["conversation_id"] in ids


@pytest.mark.asyncio
async def test_get_conversation_details_and_history(client: AsyncClient):
    res = await client.post("/api/conversations", json={"title": "Detail Test"})
    convo_id = res.json()["conversation_id"]

    detail_res = await client.get(f"/api/conversations/{convo_id}")
    assert detail_res.status_code == 200
    data = detail_res.json()
    assert data["conversation_id"] == convo_id
    assert data["title"] == "Detail Test"
    assert data["summary"] == ""
    assert isinstance(data["messages"], list)
    assert len(data["messages"]) == 0


@pytest.mark.asyncio
async def test_get_nonexistent_conversation(client: AsyncClient):
    response = await client.get("/api/conversations/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_delete_conversation(client: AsyncClient):
    res = await client.post("/api/conversations")
    convo_id = res.json()["conversation_id"]

    del_res = await client.delete(f"/api/conversations/{convo_id}")
    assert del_res.status_code == 204

    # Subsequent GET should return 404
    get_res = await client.get(f"/api/conversations/{convo_id}")
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_conversation(client: AsyncClient):
    del_res = await client.delete("/api/conversations/00000000-0000-0000-0000-000000000000")
    assert del_res.status_code == 404
