import asyncio
import logging
from typing import Any, Optional

import openai
from openai import AsyncOpenAI
from openai.types.shared_params.reasoning import Reasoning

from app.config import get_settings
from app.prompts import SUMMARY_INSTRUCTION

logger = logging.getLogger(__name__)

# Server-side configuration for intelligence modes using OpenAI Responses API
# swift: gpt-6-luna, low reasoning, 1024 output tokens
# balanced: gpt-6-luna, medium reasoning, 2048 output tokens
# deep: gpt-6-luna, high reasoning, 4096 output tokens
MODE_CONFIG: dict[str, dict[str, Any]] = {
    "swift": {
        "reasoning_effort": "low",
        "max_output_tokens": 1024,
        "label_suffix": "Swift · Low Reasoning",
    },
    "balanced": {
        "reasoning_effort": "medium",
        "max_output_tokens": 2048,
        "label_suffix": "Balanced · Medium Reasoning",
    },
    "deep": {
        "reasoning_effort": "high",
        "max_output_tokens": 4096,
        "label_suffix": "Deep · High Reasoning",
    },
}

DEFAULT_MODEL = "gpt-6-luna"

# Error types that represent transient, retryable failures
TRANSIENT_ERRORS = (
    openai.APIConnectionError,
    openai.APITimeoutError,
    openai.InternalServerError,
)


class LLMProviderError(Exception):
    """Raised when the LLM provider fails, rejects credentials, or returns unusable text."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def get_client() -> AsyncOpenAI:
    """Lazily instantiate the AsyncOpenAI client with validation."""
    settings = get_settings()
    api_key = (settings.openai_api_key or "").strip()
    if not api_key or api_key in (
        "replace_with_your_openai_api_key",
        "your_openai_api_key_here",
    ):
        raise LLMProviderError(
            "OPENAI_API_KEY is not configured. Please add your OpenAI API key to backend/.env",
            status_code=503,
        )
    return AsyncOpenAI(api_key=api_key, max_retries=0)  # We control bounded retries explicitly


def _map_api_error(exc: Exception) -> LLMProviderError:
    """Map provider exceptions to sanitized, meaningful LLMProviderError instances."""
    if isinstance(exc, (openai.AuthenticationError, openai.PermissionDeniedError)):
        return LLMProviderError(
            "The AI provider rejected the API key or credentials. Please verify your OPENAI_API_KEY.",
            status_code=502,
        )
    if isinstance(exc, openai.RateLimitError):
        return LLMProviderError(
            "The AI provider rate limit was reached. Please wait a moment and try again.",
            status_code=429,
        )
    if isinstance(exc, openai.APITimeoutError):
        return LLMProviderError(
            "The AI provider timed out. Please try again.",
            status_code=504,
        )
    if isinstance(exc, openai.APIConnectionError):
        return LLMProviderError(
            "Network error communicating with the AI service. Please check connectivity and try again.",
            status_code=502,
        )
    if isinstance(exc, openai.InternalServerError):
        return LLMProviderError(
            "The AI provider is temporarily unavailable. Please try again shortly.",
            status_code=502,
        )
    if isinstance(exc, openai.BadRequestError):
        err_msg = str(exc)
        return LLMProviderError(
            f"The AI request was rejected by the provider: {err_msg}",
            status_code=400,
        )

    # Check status_code attribute if present
    status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if status_code in (401, 403):
        return LLMProviderError(
            "The AI provider rejected the API key or credentials. Please verify your OPENAI_API_KEY.",
            status_code=502,
        )
    if status_code == 429:
        return LLMProviderError(
            "The AI provider rate limit was reached. Please wait a moment and try again.",
            status_code=429,
        )
    if status_code in (500, 502, 503, 504):
        return LLMProviderError(
            "The AI provider is temporarily unavailable. Please try again shortly.",
            status_code=502,
        )

    logger.warning("Unmapped OpenAI error (%s): %s", type(exc).__name__, exc)
    return LLMProviderError(
        "An error occurred while communicating with the AI service. Please try again.",
        status_code=502,
    )


async def _call_responses_api_with_retry(
    client: AsyncOpenAI,
    *,
    model: str,
    input_messages: list[dict[str, str]],
    instructions: str,
    max_output_tokens: int,
    reasoning_effort: Optional[str] = None,
    timeout: float = 45.0,
    max_retries: int = 2,
) -> str:
    """Execute a request to client.responses.create with bounded retries for transient errors only."""
    reasoning_param: Optional[Reasoning] = (
        {"effort": reasoning_effort} if reasoning_effort else None
    )

    attempt = 0
    backoff = 0.5
    while True:
        try:
            response = await asyncio.wait_for(
                client.responses.create(
                    model=model,
                    input=input_messages,
                    instructions=instructions,
                    max_output_tokens=max_output_tokens,
                    reasoning=reasoning_param,
                ),
                timeout=timeout,
            )
            result = response.output_text
            if not result or not result.strip():
                raise LLMProviderError(
                    "The model returned an empty response. Please try rephrasing.",
                    status_code=502,
                )
            return result.strip()
        except asyncio.TimeoutError as exc:
            attempt += 1
            if attempt > max_retries:
                logger.error("OpenAI responses.create timed out after %d attempts", attempt)
                raise LLMProviderError(
                    "The AI provider timed out. Please try again.",
                    status_code=504,
                ) from exc
            logger.warning("OpenAI responses.create timed out (attempt %d/%d). Retrying...", attempt, max_retries + 1)
            await asyncio.sleep(backoff)
            backoff *= 2
        except TRANSIENT_ERRORS as exc:
            attempt += 1
            if attempt > max_retries:
                logger.error("OpenAI transient error exhausted %d retries: %s", max_retries, exc)
                raise _map_api_error(exc) from exc
            logger.warning(
                "OpenAI transient error (%s: %s). Retry %d/%d in %.1fs...",
                type(exc).__name__,
                exc,
                attempt,
                max_retries,
                backoff,
            )
            await asyncio.sleep(backoff)
            backoff *= 2
        except (openai.AuthenticationError, openai.PermissionDeniedError, openai.BadRequestError) as exc:
            # Permanent errors: NEVER retry
            logger.error("OpenAI permanent error (%s): %s", type(exc).__name__, exc)
            raise _map_api_error(exc) from exc
        except LLMProviderError:
            raise
        except Exception as exc:
            logger.exception("Unexpected error during OpenAI responses.create call")
            raise _map_api_error(exc) from exc


async def generate_reply(
    contents: list[dict[str, str]],
    system_instruction: str,
    mode: str = "balanced",
    timeout_seconds: float = 45.0,
) -> tuple[str, str, str]:
    """Generate a chat reply using OpenAI Responses API with mode routing and reasoning configuration.

    Returns:
        tuple[str, str, str]: (reply_text, mode_name, model_label)
    """
    mode_clean = (mode or "balanced").strip().lower()
    if mode_clean not in MODE_CONFIG:
        raise LLMProviderError(
            f"Unsupported intelligence mode '{mode}'. Must be swift, balanced, or deep.",
            status_code=422,
        )

    cfg = MODE_CONFIG[mode_clean]
    settings = get_settings()
    client = get_client()

    model_id = (settings.openai_model or DEFAULT_MODEL).strip()
    reasoning_effort = cfg["reasoning_effort"]
    model_label = f"{model_id} ({cfg['label_suffix']})"

    reply_text = await _call_responses_api_with_retry(
        client,
        model=model_id,
        input_messages=contents,
        instructions=system_instruction,
        max_output_tokens=cfg["max_output_tokens"],
        reasoning_effort=reasoning_effort,
        timeout=timeout_seconds,
    )
    return reply_text, mode_clean, model_label


async def summarize_text(
    existing_summary: str,
    messages: list[tuple[str, str]],
    timeout_seconds: float = 45.0,
) -> str:
    """Condense older conversation turns into a rolling context memory summary using OpenAI Responses API."""
    settings = get_settings()
    client = get_client()
    model_id = (settings.openai_model or DEFAULT_MODEL).strip()

    transcript_lines = []
    for role, content in messages:
        label = "User" if role.lower() == "user" else "Assistant"
        transcript_lines.append(f"{label}: {content}")
    transcript = "\n".join(transcript_lines)

    prompt = (
        f"Existing conversation memory summary:\n"
        f"{existing_summary if existing_summary else '(None - this is the start of memory)'}\n\n"
        f"New conversation turns to incorporate:\n"
        f"{transcript}\n\n"
        f"Provide the updated cumulative factual summary:"
    )

    input_messages = [{"role": "user", "content": prompt}]

    return await _call_responses_api_with_retry(
        client,
        model=model_id,
        input_messages=input_messages,
        instructions=SUMMARY_INSTRUCTION,
        max_output_tokens=512,
        reasoning_effort="low",  # Low reasoning effort for factual rolling summarization
        timeout=timeout_seconds,
    )


def estimate_tokens(text: str) -> int:
    """Heuristic token estimation (~4 characters per token)."""
    return max(1, (len(text) + 3) // 4)

