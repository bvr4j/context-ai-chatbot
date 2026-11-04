import os
from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent


def normalize_database_url(url: str) -> str:
    """Normalize a database URL for SQLAlchemy with psycopg 3."""
    if not url:
        return url
    stripped = url.strip()
    if stripped.startswith("postgres://"):
        return "postgresql+psycopg://" + stripped[len("postgres://"):]
    if stripped.startswith("postgresql://") and not stripped.startswith("postgresql+"):
        return "postgresql+psycopg://" + stripped[len("postgresql://"):]
    return stripped


class Settings(BaseSettings):
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    gemini_flash_model: str = "gemini-3.8-flash"
    gemini_pro_model: str = "gemini-3.1-pro-preview"
    database_url: str = ""
    database_url_unpooled: str = ""
    app_env: str = "development"
    frontend_origin: str = "http://localhost:3000"
    max_context_messages: int = 12
    summary_trigger_messages: int = 16
    max_message_chars: int = 8000
    archive_old_messages: bool = True

    model_config = SettingsConfigDict(
        env_file=(
            str(REPO_ROOT / ".env"),
            str(BACKEND_DIR / ".env"),
            ".env",
            str(REPO_ROOT / ".env.local"),
            str(BACKEND_DIR / ".env.local"),
            ".env.local",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_and_normalize_database(self) -> "Settings":
        is_prod = (
            bool(os.getenv("VERCEL"))
            or self.app_env.lower().strip() in ("production", "prod")
        )
        raw_db_url = (self.database_url or "").strip()

        if is_prod:
            if not raw_db_url:
                raise ValueError(
                    "DATABASE_URL environment variable is required in production (VERCEL or APP_ENV=production). Never falling back to SQLite."
                )
            if raw_db_url.startswith("sqlite"):
                raise ValueError(
                    "SQLite cannot be used in production (VERCEL or APP_ENV=production). A valid PostgreSQL DATABASE_URL is required."
                )
            self.database_url = normalize_database_url(raw_db_url)
        else:
            if raw_db_url:
                self.database_url = normalize_database_url(raw_db_url)
            else:
                self.database_url = "sqlite:///./contextai.db"

        if self.database_url_unpooled:
            self.database_url_unpooled = normalize_database_url(self.database_url_unpooled)

        return self

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_production(self) -> bool:
        return (
            bool(os.getenv("VERCEL"))
            or self.app_env.lower().strip() in ("production", "prod")
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
