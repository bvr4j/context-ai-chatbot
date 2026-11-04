import os
import sys
import tempfile
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend directory is in sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import Settings, get_settings
from app.database import Base, get_db
from app.main import app


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    return Settings(
        openai_api_key="test-openai-key-12345",
        openai_model="gpt-6-luna",
        database_url="sqlite:///:memory:",
        app_env="testing",
        frontend_origin="http://localhost:5173",
        max_context_messages=4,
        summary_trigger_messages=6,
        max_message_chars=500,
        archive_old_messages=True,
    )


@pytest.fixture
def db_engine():
    """Create a fresh in-memory SQLite database engine with foreign keys enabled."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        if hasattr(dbapi_connection, "cursor"):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    """Provide an isolated database session for a test."""
    TestingSessionLocal = sessionmaker(
        bind=db_engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest_asyncio.fixture
async def client(db_session, test_settings) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async test client with overridden dependencies."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_get_settings():
        return test_settings

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = override_get_settings

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def mock_openai():
    """Default mock for OpenAI API calls to prevent any outbound network requests."""
    with patch("app.routes.chat.generate_reply", new_callable=AsyncMock) as mock_gen, \
         patch("app.memory.summarize_text", new_callable=AsyncMock) as mock_sum, \
         patch("app.openai_client.generate_reply", new_callable=AsyncMock) as mock_client_gen, \
         patch("app.openai_client.summarize_text", new_callable=AsyncMock) as mock_client_sum:

        mock_gen.return_value = ("This is a mock assistant reply.", "balanced", "gpt-6-luna (Balanced · Medium Reasoning)")
        mock_sum.return_value = "This is an updated conversation summary."
        mock_client_gen.return_value = ("This is a mock assistant reply.", "balanced", "gpt-6-luna (Balanced · Medium Reasoning)")
        mock_client_sum.return_value = "This is an updated conversation summary."

        yield {
            "generate_reply": mock_gen,
            "summarize_text": mock_sum,
        }


@pytest.fixture
def mock_gemini(mock_openai):
    """Backward-compatible fixture alias for tests referencing mock_gemini."""
    return mock_openai
