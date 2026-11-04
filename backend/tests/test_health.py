import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_endpoint(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "contextai-api"
    assert "version" in data
    assert "model" in data
    assert data["model"] == "gpt-6-luna"
    assert data["llm_provider"] == "openai"
    assert data["llm_configured"] is True
    # Verify no credentials or API keys exposed in health payload
    assert "sk-" not in str(data)
    assert "api_key" not in str(data).lower()


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["docs"] == "/docs"
