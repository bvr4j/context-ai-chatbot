from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
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
            conv_cols = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(conversations)").fetchall()]
            if "title" not in conv_cols:
                conn.exec_driver_sql("ALTER TABLE conversations ADD COLUMN title VARCHAR(255) DEFAULT 'New Conversation' NOT NULL")
        except Exception:
            pass

        try:
            msg_cols = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(messages)").fetchall()]
            if "is_archived" not in msg_cols:
                conn.exec_driver_sql("ALTER TABLE messages ADD COLUMN is_archived BOOLEAN DEFAULT 0 NOT NULL")
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

# CORS configuration
allowed_origins = [settings.frontend_origin]
if settings.app_env == "development":
    for dev_origin in ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]:
        if dev_origin not in allowed_origins:
            allowed_origins.append(dev_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
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
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "contextai-api",
        "version": "0.1.0",
        "model": settings.gemini_model,
        "environment": settings.app_env,
    }
