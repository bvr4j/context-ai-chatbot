"""Manual Live Integration Test with Google Gemini API.

This test makes a real outbound call to Google's Gemini API to verify credentials,
model compatibility, response quality, and rolling summarization.

To run:
    python backend/tests/test_gemini_live.py
or:
    pytest backend/tests/test_gemini_live.py -s
"""

import asyncio
import os
import sys
from pathlib import Path

# Ensure backend directory is in path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest
from google.genai import types

from app.config import get_settings
from app.gemini import generate_reply, get_client, summarize_text
from app.prompts import SYSTEM_INSTRUCTION


def is_live_key_available() -> bool:
    # Live tests make real external API calls and consume quota; run explicitly via:
    # RUN_LIVE_GEMINI_TESTS=1 pytest backend/tests/test_gemini_live.py
    # or: python backend/tests/test_gemini_live.py
    if os.getenv("RUN_LIVE_GEMINI_TESTS", "").lower() not in ("1", "true", "yes"):
        return False
    settings = get_settings()
    key = (settings.gemini_api_key or os.getenv("GEMINI_API_KEY", "")).strip()
    return bool(key and key not in ("replace_with_your_gemini_api_key", "your_gemini_api_key_here"))


@pytest.mark.skipif(not is_live_key_available(), reason="GEMINI_API_KEY is not configured with a real key.")
@pytest.mark.asyncio
async def test_live_gemini_reply():
    """Verify live communication with the configured Gemini model."""
    settings = get_settings()
    print(f"\n[LIVE TEST] Using model: {settings.gemini_model}")

    contents = [
        types.Content(
            role="user",
            parts=[types.Part(text="Explain what an asynchronous API is in one concise sentence.")],
        )
    ]

    reply, mode, label = await generate_reply(contents, SYSTEM_INSTRUCTION)
    print(f"[LIVE TEST] Reply received ({label}):\n{reply}")
    assert reply is not None
    assert len(reply.strip()) > 10


@pytest.mark.skipif(not is_live_key_available(), reason="GEMINI_API_KEY is not configured with a real key.")
@pytest.mark.asyncio
async def test_live_gemini_summarization():
    """Verify live rolling summarization with Gemini."""
    transcript = [
        ("user", "My name is Priya and I work on data pipelines in Bangalore."),
        ("assistant", "Nice to meet you Priya! How can I help with your data pipelines?"),
        ("user", "We are migrating from batch MapReduce to streaming Apache Flink."),
        ("assistant", "Flink provides true event-driven stream processing with low latency."),
    ]

    summary = await summarize_text(existing_summary="", messages=transcript)
    print(f"\n[LIVE TEST] Generated summary:\n{summary}")
    assert summary is not None
    assert len(summary.strip()) > 10
    # Summary should mention either Priya, Flink, or Bangalore
    summary_lower = summary.lower()
    assert any(term in summary_lower for term in ["priya", "flink", "data", "pipeline"])


if __name__ == "__main__":
    settings = get_settings()
    key = (settings.gemini_api_key or os.getenv("GEMINI_API_KEY", "")).strip()
    if not key or key in ("replace_with_your_gemini_api_key", "your_gemini_api_key_here"):
        print("WARNING: GEMINI_API_KEY is not configured or contains placeholder text.")
        print("Set your key in backend/.env to run this live integration test.")
        sys.exit(0)

    print("Running live Gemini API integration tests...")
    asyncio.run(test_live_gemini_reply())
    asyncio.run(test_live_gemini_summarization())
    print("\n[SUCCESS] Live Gemini API integration tests passed successfully!")
