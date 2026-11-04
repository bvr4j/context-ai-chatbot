from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models import Conversation
from app.openai_client import MODE_CONFIG, generate_reply


@pytest.mark.asyncio
async def test_swift_mode_routing():
    """Verify Swift mode routes to gpt-6-luna with low reasoning and 1024 max tokens."""
    contents = [{"role": "user", "content": "Hello"}]

    with patch("app.openai_client._call_responses_api_with_retry", new_callable=AsyncMock) as mock_api, \
         patch("app.openai_client.get_client"):
        mock_api.return_value = "Swift response"

        reply, mode, label = await generate_reply(
            contents, "System instruction", mode="swift"
        )

        assert reply == "Swift response"
        assert mode == "swift"
        assert "gpt-6-luna" in label
        assert "Swift · Low Reasoning" in label

        mock_api.assert_called_once()
        kwargs = mock_api.call_args[1]
        assert kwargs["model"] == "gpt-6-luna"
        assert kwargs["reasoning_effort"] == "low"
        assert kwargs["max_output_tokens"] == 1024
        assert kwargs["instructions"] == "System instruction"
        assert kwargs["input_messages"] == contents


@pytest.mark.asyncio
async def test_balanced_mode_routing():
    """Verify Balanced mode routes to gpt-6-luna with medium reasoning and 2048 max tokens."""
    contents = [{"role": "user", "content": "Hello"}]

    with patch("app.openai_client._call_responses_api_with_retry", new_callable=AsyncMock) as mock_api, \
         patch("app.openai_client.get_client"):
        mock_api.return_value = "Balanced response"

        reply, mode, label = await generate_reply(
            contents, "System instruction", mode="balanced"
        )

        assert reply == "Balanced response"
        assert mode == "balanced"
        assert "gpt-6-luna" in label
        assert "Balanced · Medium Reasoning" in label

        mock_api.assert_called_once()
        kwargs = mock_api.call_args[1]
        assert kwargs["model"] == "gpt-6-luna"
        assert kwargs["reasoning_effort"] == "medium"
        assert kwargs["max_output_tokens"] == 2048


@pytest.mark.asyncio
async def test_deep_mode_routing():
    """Verify Deep mode routes to gpt-6-luna with high reasoning and 4096 max tokens."""
    contents = [{"role": "user", "content": "Complex logic problem"}]

    with patch("app.openai_client._call_responses_api_with_retry", new_callable=AsyncMock) as mock_api, \
         patch("app.openai_client.get_client"):
        mock_api.return_value = "Deep reasoning response"

        reply, mode, label = await generate_reply(
            contents, "System instruction", mode="deep"
        )

        assert reply == "Deep reasoning response"
        assert mode == "deep"
        assert "gpt-6-luna" in label
        assert "Deep · High Reasoning" in label

        mock_api.assert_called_once()
        kwargs = mock_api.call_args[1]
        assert kwargs["model"] == "gpt-6-luna"
        assert kwargs["reasoning_effort"] == "high"
        assert kwargs["max_output_tokens"] == 4096


@pytest.mark.asyncio
async def test_invalid_mode_rejected(client: AsyncClient):
    """Verify unsupported modes are rejected with HTTP 422."""
    res = await client.post("/api/conversations")
    convo_id = res.json()["conversation_id"]

    # Invalid mode in /api/chat
    response = await client.post(
        "/api/chat",
        json={"conversation_id": convo_id, "message": "Test", "mode": "unsupported_mode"},
    )
    assert response.status_code == 422

    # Invalid mode in POST /api/conversations
    bad_create = await client.post(
        "/api/conversations",
        json={"title": "Bad Mode", "mode": "turbo_plus"},
    )
    assert bad_create.status_code == 422

    # Invalid mode in PATCH /api/conversations/{id}/mode
    bad_patch = await client.patch(
        f"/api/conversations/{convo_id}/mode",
        json={"mode": "magic"},
    )
    assert bad_patch.status_code == 422


@pytest.mark.asyncio
async def test_mode_persistence_and_retrieval(client: AsyncClient, mock_openai, db_session: Session):
    """Verify initial mode creation, persistence in database, and retrieval."""
    res = await client.post(
        "/api/conversations",
        json={"title": "Deep Analysis Session", "mode": "deep"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["mode"] == "deep"
    convo_id = data["conversation_id"]

    # Verify directly in SQLite/Postgres model
    conv_db = db_session.get(Conversation, convo_id)
    assert conv_db is not None
    assert conv_db.mode == "deep"

    # Verify in GET /api/conversations/{id}
    detail_res = await client.get(f"/api/conversations/{convo_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["mode"] == "deep"

    # Verify in GET /api/conversations list
    list_res = await client.get("/api/conversations")
    assert list_res.status_code == 200
    items = list_res.json()
    matched = next((item for item in items if item["id"] == convo_id), None)
    assert matched is not None
    assert matched["mode"] == "deep"


@pytest.mark.asyncio
async def test_mode_switching_preserves_history(client: AsyncClient, mock_openai, db_session: Session):
    """Verify switching modes updates conversation mode without resetting or fragmenting history."""
    res = await client.post(
        "/api/conversations",
        json={"title": "Multi-mode Chat", "mode": "swift"},
    )
    convo_id = res.json()["conversation_id"]

    # Turn 1: Swift
    mock_openai["generate_reply"].return_value = (
        "Quick answer", "swift", "gpt-6-luna (Swift · Low Reasoning)"
    )
    chat1 = await client.post(
        "/api/chat",
        json={"conversation_id": convo_id, "message": "Quick question", "mode": "swift"},
    )
    assert chat1.status_code == 200
    assert chat1.json()["mode"] == "swift"

    # Switch mode via PATCH endpoint to deep
    patch_res = await client.patch(
        f"/api/conversations/{convo_id}/mode",
        json={"mode": "deep"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["mode"] == "deep"

    # Turn 2: Deep
    mock_openai["generate_reply"].return_value = (
        "Deep complex analysis", "deep", "gpt-6-luna (Deep · High Reasoning)"
    )
    chat2 = await client.post(
        "/api/chat",
        json={"conversation_id": convo_id, "message": "Now analyze in detail", "mode": "deep"},
    )
    assert chat2.status_code == 200
    assert chat2.json()["mode"] == "deep"
    assert "gpt-6-luna" in chat2.json()["model_label"]

    # Verify full history is intact (4 messages: 2 user + 2 assistant)
    hist_res = await client.get(f"/api/conversations/{convo_id}")
    assert hist_res.status_code == 200
    hist = hist_res.json()
    assert len(hist["messages"]) == 4
    assert hist["mode"] == "deep"
    assert hist["messages"][0]["content"] == "Quick question"
    assert hist["messages"][1]["content"] == "Quick answer"
    assert hist["messages"][2]["content"] == "Now analyze in detail"
    assert hist["messages"][3]["content"] == "Deep complex analysis"


@pytest.mark.asyncio
async def test_chat_response_contract_metadata(client: AsyncClient, mock_openai):
    """Verify ChatResponse returns all required metadata fields."""
    res = await client.post("/api/conversations")
    convo_id = res.json()["conversation_id"]

    mock_openai["generate_reply"].return_value = (
        "Balanced reply", "balanced", "gpt-6-luna (Balanced · Medium Reasoning)"
    )

    chat_res = await client.post(
        "/api/chat",
        json={"conversation_id": convo_id, "message": "Hello!", "mode": "balanced"},
    )
    assert chat_res.status_code == 200
    body = chat_res.json()

    assert "conversation_id" in body
    assert "id" in body
    assert body["reply"] == "Balanced reply"
    assert body["mode"] == "balanced"
    assert body["model_label"] == "gpt-6-luna (Balanced · Medium Reasoning)"
    assert "context_summary" in body
    assert "messages_in_context" in body
    assert body["messages_in_context"] == 2


@pytest.mark.asyncio
async def test_mode_config_reasoning_levels():
    """Verify each mode has the correct reasoning level and output token configuration."""
    assert MODE_CONFIG["swift"]["reasoning_effort"] == "low"
    assert MODE_CONFIG["swift"]["max_output_tokens"] == 1024

    assert MODE_CONFIG["balanced"]["reasoning_effort"] == "medium"
    assert MODE_CONFIG["balanced"]["max_output_tokens"] == 2048

    assert MODE_CONFIG["deep"]["reasoning_effort"] == "high"
    assert MODE_CONFIG["deep"]["max_output_tokens"] == 4096
