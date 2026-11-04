from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import Base, engine, get_db
from app.openai_client import LLMProviderError
from app.models import Conversation, Message  # noqa: F401 - register ORM metadata
from app.routes.chat import router as chat_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan handler for FastAPI application."""
    if settings.is_sqlite:
        # In local SQLite development, initialize tables if not already present
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="ContextAI API",
    description="A stateful, context-aware multi-turn chatbot powered by OpenAI and persistent memory.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration supporting localhost development (ports 3000 & 5173) and configured origins
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
def health_check(
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    db_healthy = True
    db_dialect = "unknown"
    try:
        bind = db.get_bind()
        db_dialect = bind.dialect.name
        db.execute(text("SELECT 1"))
    except Exception:
        db_healthy = False
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    overall_status = "ok" if db_healthy else "unhealthy"

    return {
        "status": overall_status,
        "service": "contextai-api",
        "version": "0.1.0",
        "environment": settings.app_env,
        "database": db_dialect,
        "database_status": "healthy" if db_healthy else "unhealthy",
        "llm_provider": "openai",
        "llm_configured": bool(
            settings.openai_api_key
            and settings.openai_api_key.strip()
            not in ("", "replace_with_your_openai_api_key", "your_openai_api_key_here")
        ),
        "model": settings.openai_model,
        "supported_modes": ["swift", "balanced", "deep"],
    }
