from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.config import Settings, get_settings
from app.database import Base, get_db
from app.main import app
from app.models import Conversation, Message


@pytest.mark.asyncio
async def test_backend_restart_persistence(tmp_path: Path):
    """Test that conversation state and message history survive a complete backend restart."""
    db_file = tmp_path / "test_persistence.db"
    db_url = f"sqlite:///{db_file.as_posix()}"

    settings_instance = Settings(
        gemini_api_key="test-api-key",
        gemini_model="gemini-2.5-flash",
        database_url=db_url,
        app_env="testing",
        frontend_origin="http://localhost:5173",
        max_context_messages=10,
        summary_trigger_messages=14,
        max_message_chars=1000,
        archive_old_messages=True,
    )

    # --- Phase 1: Initial Backend Lifetime ---
    engine1 = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine1)
    SessionMaker1 = sessionmaker(bind=engine1, autoflush=False, autocommit=False)

    def get_db_override1():
        db = SessionMaker1()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = get_db_override1
    app.dependency_overrides[get_settings] = lambda: settings_instance

    convo_id = None
    with patch("app.routes.chat.generate_reply", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "Nice to meet you, Dave! I have noted that you are working on ContextAI."

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client1:
            # Create conversation
            res_create = await client1.post("/api/conversations", json={"title": "Restart Test Session"})
            assert res_create.status_code == 201
            convo_id = res_create.json()["conversation_id"]

            # Send first message
            res_chat = await client1.post(
                "/api/chat",
                json={"conversation_id": convo_id, "message": "My name is Dave and I am building ContextAI."},
            )
            assert res_chat.status_code == 200

    # Simulate shutting down the backend process completely
    app.dependency_overrides.clear()
    engine1.dispose()

    # --- Phase 2: Backend Reboots Freshly ---
    engine2 = create_engine(db_url, connect_args={"check_same_thread": False})
    SessionMaker2 = sessionmaker(bind=engine2, autoflush=False, autocommit=False)

    def get_db_override2():
        db = SessionMaker2()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = get_db_override2
    app.dependency_overrides[get_settings] = lambda: settings_instance

    with patch("app.routes.chat.generate_reply", new_callable=AsyncMock) as mock_gen2:
        mock_gen2.return_value = "Your name is Dave and you are building ContextAI."

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client2:
            # Retrieve conversation history after restart
            res_get = await client2.get(f"/api/conversations/{convo_id}")
            assert res_get.status_code == 200
            data = res_get.json()
            assert data["conversation_id"] == convo_id
            assert data["title"] == "Restart Test Session"
            assert len(data["messages"]) == 2
            assert data["messages"][0]["content"] == "My name is Dave and I am building ContextAI."

            # Send follow-up turn in the restarted session
            res_chat2 = await client2.post(
                "/api/chat",
                json={"conversation_id": convo_id, "message": "What is my name?"},
            )
            assert res_chat2.status_code == 200
            assert res_chat2.json()["reply"] == "Your name is Dave and you are building ContextAI."

            # Verify total messages after 2nd turn
            res_get2 = await client2.get(f"/api/conversations/{convo_id}")
            assert len(res_get2.json()["messages"]) == 4

    app.dependency_overrides.clear()
    engine2.dispose()
