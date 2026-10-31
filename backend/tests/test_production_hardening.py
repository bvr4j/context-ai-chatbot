import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from dotenv import dotenv_values
from fastapi import status
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import Settings, get_settings, normalize_database_url
from app.database import Base, get_db
from app.main import app


def test_postgresql_url_normalization():
    """Verify that PostgreSQL URLs are correctly normalized for psycopg 3."""
    # postgresql:// -> postgresql+psycopg://
    url1 = "postgresql://user:pass@ep-bitter.neon.tech/neondb?sslmode=require"
    assert normalize_database_url(url1) == "postgresql+psycopg://user:pass@ep-bitter.neon.tech/neondb?sslmode=require"

    # postgres:// -> postgresql+psycopg://
    url2 = "postgres://user:pass@ep-bitter.neon.tech/neondb"
    assert normalize_database_url(url2) == "postgresql+psycopg://user:pass@ep-bitter.neon.tech/neondb"

    # already postgresql+psycopg:// -> unchanged
    url3 = "postgresql+psycopg://user:pass@ep-bitter.neon.tech/neondb"
    assert normalize_database_url(url3) == url3

    # SQLite -> unchanged
    assert normalize_database_url("sqlite:///./test.db") == "sqlite:///./test.db"
    assert normalize_database_url("sqlite:///:memory:") == "sqlite:///:memory:"
    assert normalize_database_url("") == ""


def test_production_missing_database_url(monkeypatch):
    """Verify that production environments strictly require a PostgreSQL DATABASE_URL."""
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.setenv("APP_ENV", "production")

    # Missing database_url in production must raise ValueError
    with pytest.raises(ValueError, match="DATABASE_URL environment variable is required in production"):
        Settings(app_env="production", database_url="")

    # Silent fallback to SQLite in production must be forbidden
    with pytest.raises(ValueError, match="SQLite cannot be used in production"):
        Settings(app_env="production", database_url="sqlite:///./contextai.db")

    # Vercel environment without DATABASE_URL must raise ValueError
    monkeypatch.setenv("VERCEL", "1")
    with pytest.raises(ValueError, match="DATABASE_URL environment variable is required in production"):
        Settings(app_env="development", database_url="")


def test_sqlite_local_development(monkeypatch):
    """Verify that SQLite is used exclusively for local development when no DATABASE_URL is set."""
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    dev_settings = Settings(
        app_env="development",
        database_url="",
        _env_file=None,  # Do not read .env.local for this pure dev test
    )
    assert dev_settings.is_sqlite is True
    assert dev_settings.is_production is False
    assert dev_settings.database_url == "sqlite:///./contextai.db"


@pytest.mark.asyncio
async def test_health_endpoint_healthy(client: AsyncClient):
    """Verify that /health reports actual database dialect and healthy status."""
    res = await client.get("/health")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["status"] == "ok"
    assert data["database"] == "sqlite"
    assert data["database_status"] == "healthy"
    assert "password" not in str(data).lower()
    assert "neon.tech" not in str(data)


@pytest.mark.asyncio
async def test_health_endpoint_database_failure(test_settings):
    """Verify that /health returns 503 and unhealthy status when database connectivity fails."""
    def broken_get_db():
        mock_session = MagicMock(spec=Session)
        mock_bind = MagicMock()
        mock_bind.dialect.name = "postgresql"
        mock_session.get_bind.return_value = mock_bind
        mock_session.execute.side_effect = Exception("Connection to Neon database timed out")
        try:
            yield mock_session
        finally:
            pass

    app.dependency_overrides[get_db] = broken_get_db
    app.dependency_overrides[get_settings] = lambda: test_settings

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/health")

    app.dependency_overrides.clear()

    assert res.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    data = res.json()
    assert data["status"] == "unhealthy"
    assert data["database_status"] == "unhealthy"
    assert data["database"] == "postgresql"
    # Credentials or sensitive host URLs must NOT be exposed
    assert "password" not in str(data).lower()
    assert "postgres://" not in str(data)


def test_alembic_configuration_integrity():
    """Verify Alembic configuration files and initial migration exist and are valid."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    alembic_ini = repo_root / "alembic.ini"
    assert alembic_ini.exists(), "alembic.ini must exist in the project root"

    alembic_env = repo_root / "backend" / "alembic" / "env.py"
    assert alembic_env.exists(), "backend/alembic/env.py must exist"

    versions_dir = repo_root / "backend" / "alembic" / "versions"
    assert versions_dir.exists(), "backend/alembic/versions must exist"

    migrations = list(versions_dir.glob("*.py"))
    assert len(migrations) >= 1, "At least one Alembic migration must exist"

    initial_mig = versions_dir / "001_initial_schema.py"
    assert initial_mig.exists(), "001_initial_schema.py must exist"
    content = initial_mig.read_text(encoding="utf-8")
    assert "conversations" in content
    assert "messages" in content


@pytest.mark.asyncio
async def test_neon_postgresql_live_crud():
    """Integration test that runs live against Neon PostgreSQL if configured."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    env_local = repo_root / ".env.local"
    env_vars = dotenv_values(env_local) if env_local.exists() else {}

    raw_db_url = env_vars.get("DATABASE_URL") or os.getenv("DATABASE_URL")
    if not raw_db_url or "neon.tech" not in raw_db_url:
        pytest.skip("Neon PostgreSQL DATABASE_URL not available in environment or .env.local")

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    neon_url = normalize_database_url(raw_db_url)
    engine = create_engine(neon_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)

    def neon_get_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    neon_settings = Settings(
        app_env="development",
        database_url=neon_url,
        gemini_api_key="test-api-key",
    )

    app.dependency_overrides[get_db] = neon_get_db
    app.dependency_overrides[get_settings] = lambda: neon_settings

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health check against Neon
        health_res = await client.get("/health")
        assert health_res.status_code == 200
        assert health_res.json()["database"] == "postgresql"
        assert health_res.json()["database_status"] == "healthy"

        # 2. Create conversation in Neon
        create_res = await client.post(
            "/api/conversations",
            json={"title": "Neon Live Test", "mode": "swift"},
        )
        assert create_res.status_code == 201
        data = create_res.json()
        conv_id = data["id"]
        assert data["title"] == "Neon Live Test"
        assert data["mode"] == "swift"

        # 3. Retrieve conversation from Neon
        get_res = await client.get(f"/api/conversations/{conv_id}")
        assert get_res.status_code == 200
        assert get_res.json()["title"] == "Neon Live Test"

        # 4. Patch mode in Neon
        patch_res = await client.patch(
            f"/api/conversations/{conv_id}/mode",
            json={"mode": "deep"},
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["mode"] == "deep"

        # 5. Delete conversation from Neon
        del_res = await client.delete(f"/api/conversations/{conv_id}")
        assert del_res.status_code == 204

        # 6. Verify 404 after deletion
        get_after = await client.get(f"/api/conversations/{conv_id}")
        assert get_after.status_code == 404

    app.dependency_overrides.clear()
    engine.dispose()
