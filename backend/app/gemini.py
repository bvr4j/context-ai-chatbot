"""Deprecated Gemini provider module.

ContextAI has migrated exclusively to OpenAI (app.openai_client).
Automatic or silent fallback to Gemini is strictly prohibited.
"""

from app.openai_client import LLMProviderError


def _disabled(*args, **kwargs):
    raise LLMProviderError(
        "The Gemini provider is deprecated and disabled. ContextAI uses OpenAI exclusively.",
        status_code=500,
    )


generate_reply = _disabled
summarize_text = _disabled
get_client = _disabled
