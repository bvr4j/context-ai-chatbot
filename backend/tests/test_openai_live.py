"""Manual Live Integration Test with OpenAI Responses API.

This test makes a real outbound call to OpenAI API using AsyncOpenAI and the
Responses API (client.responses.create) to verify credentials, model compatibility,
response quality, reasoning configuration, and rolling summarization.

To run:
    python backend/tests/test_openai_live.py
or:
    RUN_LIVE_OPENAI_TESTS=1 pytest backend/tests/test_openai_live.py -s
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

from app.config import get_settings
from app.openai_client import generate_reply, get_client, summarize_text
from app.prompts import SYSTEM_INSTRUCTION


def is_live_key_available() -> bool:
    """Check if a real, valid OpenAI API key is configured."""
    # During automated test runs, skip unless explicitly enabled to avoid consuming quota
    if os.getenv("RUN_LIVE_OPENAI_TESTS", "").lower() not in ("1", "true", "yes"):
        return False
    settings = get_settings()
    key = (settings.openai_api_key or os.getenv("OPENAI_API_KEY", "")).strip()
    return bool(key and key not in ("replace_with_your_openai_api_key", "your_openai_api_key_here"))


@pytest.mark.skipif(not is_live_key_available(), reason="OPENAI_API_KEY is not configured with a real key or RUN_LIVE_OPENAI_TESTS!=1.")
@pytest.mark.asyncio
async def test_live_openai_reply():
    """Verify live communication with the configured OpenAI model using Responses API."""
    settings = get_settings()
    print(f"\n[LIVE OPENAI TEST] Using model: {settings.openai_model}")

    contents = [
        {"role": "user", "content": "Explain what an asynchronous API is in one concise sentence."}
    ]

    reply, mode, label = await generate_reply(contents, SYSTEM_INSTRUCTION, mode="balanced")
    print(f"[LIVE OPENAI TEST] Mode: {mode}, Label: {label}")
    print(f"[LIVE OPENAI TEST] Reply received:\n{reply}\n")
    assert reply is not None
    assert len(reply.strip()) > 10
    assert "gpt-6-luna" in label or settings.openai_model in label


@pytest.mark.skipif(not is_live_key_available(), reason="OPENAI_API_KEY is not configured with a real key or RUN_LIVE_OPENAI_TESTS!=1.")
@pytest.mark.asyncio
async def test_live_openai_summarization():
    """Verify live rolling summarization with OpenAI Responses API."""
    transcript = [
        ("user", "My name is Priya and I work on data pipelines in Bangalore."),
        ("assistant", "Nice to meet you Priya! How can I help with your data pipelines?"),
        ("user", "We are migrating from batch MapReduce to streaming Apache Flink."),
        ("assistant", "Flink provides true event-driven stream processing with low latency."),
    ]

    summary = await summarize_text(existing_summary="", messages=transcript)
    print(f"\n[LIVE OPENAI TEST] Generated summary:\n{summary}\n")
    assert summary is not None
    assert len(summary.strip()) > 10
    summary_lower = summary.lower()
    assert any(term in summary_lower for term in ["priya", "flink", "data", "pipeline"])


if __name__ == "__main__":
    settings = get_settings()
    key = (settings.openai_api_key or os.getenv("OPENAI_API_KEY", "")).strip()
    if not key or key in ("replace_with_your_openai_api_key", "your_openai_api_key_here"):
        print("WARNING: OPENAI_API_KEY is not configured or contains placeholder text.")
        print("Set your key in backend/.env to run this live integration test.")
        sys.exit(0)

    print("Running live OpenAI API integration smoke tests...")
    asyncio.run(test_live_openai_reply())
    asyncio.run(test_live_openai_summarization())
    print("\n[SUCCESS] Live OpenAI API smoke tests passed successfully!")

