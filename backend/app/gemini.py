import asyncio
import logging
from typing import Optional

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.config import get_settings
from app.prompts import SUMMARY_INSTRUCTION

logger = logging.getLogger(__name__)


class LLMProviderError(Exception):
    """Raised when the Gemini provider fails, rejects credentials, or returns unusable text."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def get_client() -> genai.Client:
    """Lazily instantiate the Gemini client with validation."""
    settings = get_settings()
    api_key = (settings.gemini_api_key or "").strip()
    if not api_key or api_key in ("replace_with_your_gemini_api_key", "your_gemini_api_key_here"):
        raise LLMProviderError(
            "GEMINI_API_KEY is not configured. Please add your Gemini API key to backend/.env",
            status_code=503,
        )
    return genai.Client(api_key=api_key)


def _call_gemini_generate(
    client: genai.Client,
    model: str,
    contents: list[types.Content],
    instruction: str,
    temperature: float = 0.7,
    max_output_tokens: int = 1024,
) -> str:
    """Synchronous invocation of the Google Gen AI API."""
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=instruction,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        ),
    )
    result = response.text
    if not result or not result.strip():
        raise LLMProviderError("The model returned an empty response. Please try rephrasing.")
    return result.strip()


def _map_api_error(exc: Exception) -> LLMProviderError:
    """Map provider exceptions to sanitized, meaningful LLMProviderError instances."""
    status_code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    err_str = str(exc)

    if status_code in (401, 403) or "API_KEY_INVALID" in err_str or "unregistered" in err_str:
        return LLMProviderError(
            "The AI provider rejected the API key or credentials. Please verify your GEMINI_API_KEY.",
            status_code=502,
        )
    if status_code == 429 or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
        return LLMProviderError(
            "The AI provider rate limit was reached. Please wait a moment and try again.",
            status_code=429,
        )
    if status_code in (500, 502, 503, 504) or "UNAVAILABLE" in err_str:
        return LLMProviderError(
            "The AI provider is temporarily unavailable. Please try again shortly.",
            status_code=502,
        )
    if status_code == 400 or "INVALID_ARGUMENT" in err_str:
        return LLMProviderError(
            "The AI request format was invalid for the specified model.",
            status_code=400,
        )

    logger.warning("Unmapped Gemini error (%s): %s", type(exc).__name__, exc)
    return LLMProviderError(
        "An error occurred while communicating with the AI service. Please try again.",
        status_code=502,
    )


async def generate_reply(
    contents: list[types.Content], system_instruction: str, timeout_seconds: float = 45.0
) -> str:
    """Generate a chat reply given the structured content history and system instruction."""
    settings = get_settings()
    client = get_client()

    try:
        return await asyncio.wait_for(
            asyncio.to_thread(
                _call_gemini_generate,
                client,
                settings.gemini_model,
                contents,
                system_instruction,
                0.7,
                1024,
            ),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        logger.error("Gemini generate_reply timed out after %s seconds", timeout_seconds)
        raise LLMProviderError(
            "The AI provider timed out waiting for a response. Please try again.",
            status_code=504,
        ) from exc
    except LLMProviderError:
        raise
    except Exception as exc:
        logger.exception("Gemini API call failed during generate_reply")
        raise _map_api_error(exc) from exc


async def summarize_text(
    existing_summary: str,
    messages: list[tuple[str, str]],
    timeout_seconds: float = 45.0,
) -> str:
    """Condense older conversation turns into a rolling context memory summary."""
    settings = get_settings()
    client = get_client()

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

    content = types.Content(role="user", parts=[types.Part(text=prompt)])

    try:
        return await asyncio.wait_for(
            asyncio.to_thread(
                _call_gemini_generate,
                client,
                settings.gemini_model,
                [content],
                SUMMARY_INSTRUCTION,
                0.3,
                512,
            ),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        logger.error("Gemini summarize_text timed out after %s seconds", timeout_seconds)
        raise LLMProviderError(
            "Conversation summarization timed out.",
            status_code=504,
        ) from exc
    except LLMProviderError:
        raise
    except Exception as exc:
        logger.exception("Gemini API call failed during summarize_text")
        raise _map_api_error(exc) from exc


def estimate_tokens(text: str) -> int:
    """Heuristic token estimation (~4 characters per token)."""
    return max(1, (len(text) + 3) // 4)
