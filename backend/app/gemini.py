import asyncio
import logging
from typing import Optional

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.config import get_settings
from app.prompts import SUMMARY_INSTRUCTION

logger = logging.getLogger(__name__)

# Server-side allowlist for intelligence modes
# swift: Gemini Flash, LOW thinking
# balanced: Gemini Flash, MEDIUM thinking
# deep: Gemini Pro, HIGH thinking
MODE_CONFIG = {
    "swift": {
        "model_key": "gemini_flash_model",
        "default_model": "gemini-3.8-flash",
        "thinking_level": types.ThinkingLevel.LOW,
        "thinking_name": "LOW",
        "max_output_tokens": 1024,
        "label_suffix": "Swift · Low Thinking",
    },
    "balanced": {
        "model_key": "gemini_flash_model",
        "default_model": "gemini-3.8-flash",
        "thinking_level": types.ThinkingLevel.MEDIUM,
        "thinking_name": "MEDIUM",
        "max_output_tokens": 2048,
        "label_suffix": "Balanced · Medium Thinking",
    },
    "deep": {
        "model_key": "gemini_pro_model",
        "default_model": "gemini-3.1-pro-preview",
        "thinking_level": types.ThinkingLevel.HIGH,
        "thinking_name": "HIGH",
        "max_output_tokens": 4096,
        "label_suffix": "Deep · High Thinking",
    },
}


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
    thinking_level: Optional[types.ThinkingLevel] = None,
) -> str:
    """Synchronous invocation of the Google Gen AI API with thinking configuration."""
    thinking_config = (
        types.ThinkingConfig(thinking_level=thinking_level)
        if thinking_level is not None
        else None
    )
    config = types.GenerateContentConfig(
        system_instruction=instruction,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        thinking_config=thinking_config,
    )
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=config,
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
            f"The AI request was rejected by the provider: {err_str}",
            status_code=400,
        )

    logger.warning("Unmapped Gemini error (%s): %s", type(exc).__name__, exc)
    return LLMProviderError(
        "An error occurred while communicating with the AI service. Please try again.",
        status_code=502,
    )


async def generate_reply(
    contents: list[types.Content],
    system_instruction: str,
    mode: str = "balanced",
    timeout_seconds: float = 45.0,
) -> tuple[str, str, str]:
    """Generate a chat reply with model routing and thinking configuration.
    
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

    # Route to actual configured model
    if mode_clean == "deep":
        model_id = getattr(settings, "gemini_pro_model", "gemini-3.1-pro-preview")
    else:
        model_id = getattr(
            settings, "gemini_flash_model", getattr(settings, "gemini_model", "gemini-3.8-flash")
        )

    thinking_level = cfg["thinking_level"]
    model_label = f"{model_id} ({cfg['label_suffix']})"

    try:
        reply_text = await asyncio.wait_for(
            asyncio.to_thread(
                _call_gemini_generate,
                client,
                model_id,
                contents,
                system_instruction,
                0.7,
                cfg["max_output_tokens"],
                thinking_level,
            ),
            timeout=timeout_seconds,
        )
        return reply_text, mode_clean, model_label
    except asyncio.TimeoutError as exc:
        logger.error(
            "Gemini generate_reply timed out after %s seconds for mode %s",
            timeout_seconds,
            mode_clean,
        )
        raise LLMProviderError(
            f"The AI provider timed out ({mode_clean} mode). Please try again.",
            status_code=504,
        ) from exc
    except LLMProviderError:
        raise
    except Exception as exc:
        logger.exception("Gemini API call failed during generate_reply in %s mode", mode_clean)
        raise _map_api_error(exc) from exc


async def summarize_text(
    existing_summary: str,
    messages: list[tuple[str, str]],
    timeout_seconds: float = 45.0,
) -> str:
    """Condense older conversation turns into a rolling context memory summary using flash model."""
    settings = get_settings()
    client = get_client()
    model_id = getattr(
        settings, "gemini_flash_model", getattr(settings, "gemini_model", "gemini-3.8-flash")
    )

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
                model_id,
                [content],
                SUMMARY_INSTRUCTION,
                0.3,
                512,
                None,  # No heavy thinking required for rolling summarization
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
