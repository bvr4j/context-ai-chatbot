import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent


def get_default_database_url() -> str:
    # On Vercel serverless environments, only /tmp is writable for SQLite files
    if os.getenv("VERCEL"):
        return "sqlite:////tmp/contextai.db"
    return "sqlite:///./contextai.db"


class Settings(BaseSettings):
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_flash_model: str = "gemini-2.5-flash"
    gemini_pro_model: str = "gemini-2.5-pro"
    database_url: str = get_default_database_url()
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
