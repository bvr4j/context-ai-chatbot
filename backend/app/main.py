from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.database import Base, engine
from app.gemini import LLMProviderError
from app.models import Conversation, Message  # noqa: F401 - register ORM metadata
from app.routes.chat import router as chat_router

settings = get_settings()


def init_and_migrate_db() -> None:
    """Ensure database tables and required schema columns exist."""
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        try:
            conv_cols = [
                r[1] for r in conn.exec_driver_sql("PRAGMA table_info(conversations)").fetchall()
            ]
            if "title" not in conv_cols:
                conn.exec_driver_sql(
                    "ALTER TABLE conversations ADD COLUMN title VARCHAR(255) DEFAULT 'New Conversation' NOT NULL"
                )
            if "mode" not in conv_cols:
                conn.exec_driver_sql(
                    "ALTER TABLE conversations ADD COLUMN mode VARCHAR(20) DEFAULT 'balanced' NOT NULL"
                )
        except Exception:
            pass

        try:
            msg_cols = [
                r[1] for r in conn.exec_driver_sql("PRAGMA table_info(messages)").fetchall()
            ]
            if "is_archived" not in msg_cols:
                conn.exec_driver_sql(
                    "ALTER TABLE messages ADD COLUMN is_archived BOOLEAN DEFAULT 0 NOT NULL"
                )
            if "mode" not in msg_cols:
                conn.exec_driver_sql(
                    "ALTER TABLE messages ADD COLUMN mode VARCHAR(20) DEFAULT NULL"
                )
            if "model_label" not in msg_cols:
                conn.exec_driver_sql(
                    "ALTER TABLE messages ADD COLUMN model_label VARCHAR(100) DEFAULT NULL"
                )
        except Exception:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize database tables and application resources on startup."""
    init_and_migrate_db()
    yield


app = FastAPI(
    title="ContextAI API",
    description="A stateful, context-aware multi-turn chatbot powered by Google Gemini and SQLite memory.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration supporting both Vite dev ports (3000 & 5173) and configured origins
allowed_origins = [settings.frontend_origin]
for origin in [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]:
    if origin not in allowed_origins:
        allowed_origins.append(origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(LLMProviderError)
async def llm_provider_error_handler(
    request: Request, exc: LLMProviderError
) -> JSONResponse:
    """Ensure all LLM provider errors return structured, sanitized JSON error responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


app.include_router(chat_router)


@app.get("/", tags=["system"])
def root_info() -> dict[str, str]:
    return {
        "message": "Welcome to ContextAI API",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["system"])
def health_check(settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "contextai-api",
        "version": "0.1.0",
        "environment": settings.app_env,
        "database": "sqlite",
        "llm_configured": bool(
            settings.gemini_api_key
            and settings.gemini_api_key.strip()
            not in ("", "replace_with_your_gemini_api_key", "your_gemini_api_key_here")
        ),
        "model": settings.gemini_model,
        "flash_model": settings.gemini_flash_model,
        "pro_model": settings.gemini_pro_model,
        "supported_modes": ["swift", "balanced", "deep"],
    }
