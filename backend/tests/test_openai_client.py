"""Comprehensive unit tests for the OpenAI provider implementation.

Verifies:
1. OpenAI client configuration and lazy instantiation
2. Swift, Balanced, and Deep mode routing with reasoning effort and token budgets
3. System prompt preservation via instructions parameter
4. Multi-turn context conversion to OpenAI Responses API input format
5. Rolling summarization using OpenAI Responses API
6. Provider error mapping: 401/403, 429, 500/502/503/504, network errors, timeouts
7. Bounded retries for transient errors only (never retrying permanent errors)
8. Strict absence of silent Gemini fallback
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import openai
import pytest

from app.config import Settings
from app.openai_client import (
    DEFAULT_MODEL,
    MODE_CONFIG,
    LLMProviderError,
    _call_responses_api_with_retry,
    _map_api_error,
    generate_reply,
    get_client,
    summarize_text,
)
from app.prompts import SYSTEM_INSTRUCTION


# ==============================================================================
# 1. Client Configuration Tests
# ==============================================================================

def test_get_client_valid_api_key(monkeypatch):
    """Verify AsyncOpenAI client initializes successfully when OPENAI_API_KEY is present."""
    fake_settings = Settings(openai_api_key="sk-test-valid-key-12345")
    with patch("app.openai_client.get_settings", return_value=fake_settings):
        client = get_client()
        assert isinstance(client, openai.AsyncOpenAI)
        assert client.api_key == "sk-test-valid-key-12345"


def test_get_client_missing_key_raises_503(monkeypatch):
    """Verify get_client raises a 503 LLMProviderError when OPENAI_API_KEY is missing."""
    for empty_val in ("", "   ", "replace_with_your_openai_api_key", "your_openai_api_key_here"):
        fake_settings = Settings(openai_api_key=empty_val)
        with patch("app.openai_client.get_settings", return_value=fake_settings):
            with pytest.raises(LLMProviderError) as exc_info:
                get_client()
            assert exc_info.value.status_code == 503
            assert "OPENAI_API_KEY is not configured" in exc_info.value.message


# ==============================================================================
# 2. Routing, Reasoning Effort, and Token Budgets
# ==============================================================================

@pytest.mark.asyncio
async def test_generate_reply_swift_mode():
    """Verify Swift mode: low reasoning, 1024 max tokens."""
    contents = [{"role": "user", "content": "What is Python?"}]
    mock_resp = MagicMock()
    mock_resp.output_text = "Python is a programming language."

    mock_client = AsyncMock()
    mock_client.responses.create.return_value = mock_resp

    with patch("app.openai_client.get_client", return_value=mock_client):
        reply, mode, label = await generate_reply(
            contents, SYSTEM_INSTRUCTION, mode="swift"
        )

        assert reply == "Python is a programming language."
        assert mode == "swift"
        assert "gpt-6-luna" in label
        assert "Swift · Low Reasoning" in label

        mock_client.responses.create.assert_called_once()
        kwargs = mock_client.responses.create.call_args[1]
        assert kwargs["model"] == "gpt-6-luna"
        assert kwargs["reasoning"] == {"effort": "low"}
        assert kwargs["max_output_tokens"] == 1024
        assert kwargs["instructions"] == SYSTEM_INSTRUCTION
        assert kwargs["input"] == contents


@pytest.mark.asyncio
async def test_generate_reply_balanced_mode():
    """Verify Balanced mode: medium reasoning, 2048 max tokens."""
    contents = [{"role": "user", "content": "Explain async IO."}]
    mock_resp = MagicMock()
    mock_resp.output_text = "Async IO allows cooperative multitasking."

    mock_client = AsyncMock()
    mock_client.responses.create.return_value = mock_resp

    with patch("app.openai_client.get_client", return_value=mock_client):
        reply, mode, label = await generate_reply(
            contents, SYSTEM_INSTRUCTION, mode="balanced"
        )

        assert reply == "Async IO allows cooperative multitasking."
        assert mode == "balanced"
        assert "gpt-6-luna" in label
        assert "Balanced · Medium Reasoning" in label

        kwargs = mock_client.responses.create.call_args[1]
        assert kwargs["model"] == "gpt-6-luna"
        assert kwargs["reasoning"] == {"effort": "medium"}
        assert kwargs["max_output_tokens"] == 2048


@pytest.mark.asyncio
async def test_generate_reply_deep_mode():
    """Verify Deep mode: high reasoning, 4096 max tokens."""
    contents = [{"role": "user", "content": "Solve this algorithmic puzzle."}]
    mock_resp = MagicMock()
    mock_resp.output_text = "Detailed reasoning steps and final solution."

    mock_client = AsyncMock()
    mock_client.responses.create.return_value = mock_resp

    with patch("app.openai_client.get_client", return_value=mock_client):
        reply, mode, label = await generate_reply(
            contents, SYSTEM_INSTRUCTION, mode="deep"
        )

        assert reply == "Detailed reasoning steps and final solution."
        assert mode == "deep"
        assert "gpt-6-luna" in label
        assert "Deep · High Reasoning" in label

        kwargs = mock_client.responses.create.call_args[1]
        assert kwargs["model"] == "gpt-6-luna"
        assert kwargs["reasoning"] == {"effort": "high"}
        assert kwargs["max_output_tokens"] == 4096


@pytest.mark.asyncio
async def test_generate_reply_unsupported_mode():
    """Verify unsupported mode raises 422 LLMProviderError."""
    with pytest.raises(LLMProviderError) as exc_info:
        await generate_reply([{"role": "user", "content": "Hi"}], SYSTEM_INSTRUCTION, mode="hyper_turbo")
    assert exc_info.value.status_code == 422


# ==============================================================================
# 3. System Prompt Preservation & Multi-Turn Context Conversion
# ==============================================================================

@pytest.mark.asyncio
async def test_system_prompt_passed_via_instructions():
    """Verify system instruction is strictly preserved via instructions parameter in Responses API."""
    custom_instruction = "You are a concise expert mathematician."
    contents = [
        {"role": "user", "content": "Turn 1"},
        {"role": "assistant", "content": "Reply 1"},
        {"role": "user", "content": "Turn 2"},
    ]
    mock_resp = MagicMock()
    mock_resp.output_text = "Mathematician answer."

    mock_client = AsyncMock()
    mock_client.responses.create.return_value = mock_resp

    with patch("app.openai_client.get_client", return_value=mock_client):
        await generate_reply(contents, custom_instruction, mode="balanced")

        kwargs = mock_client.responses.create.call_args[1]
        assert kwargs["instructions"] == custom_instruction
        assert kwargs["input"] == contents
        assert len(kwargs["input"]) == 3
        assert kwargs["input"][0]["role"] == "user"
        assert kwargs["input"][1]["role"] == "assistant"
        assert kwargs["input"][2]["role"] == "user"


# ==============================================================================
# 4. Rolling Summarization with OpenAI
# ==============================================================================

@pytest.mark.asyncio
async def test_summarize_text_openai():
    """Verify rolling summarization invokes OpenAI Responses API with SUMMARY_INSTRUCTION."""
    mock_resp = MagicMock()
    mock_resp.output_text = "Updated memory: User prefers Python and PostgreSQL."

    mock_client = AsyncMock()
    mock_client.responses.create.return_value = mock_resp

    messages = [
        ("user", "I work with Python."),
        ("assistant", "Python is great."),
        ("user", "We also use PostgreSQL."),
        ("assistant", "PostgreSQL is robust."),
    ]

    with patch("app.openai_client.get_client", return_value=mock_client):
        summary = await summarize_text(
            existing_summary="User works in software engineering.",
            messages=messages,
        )

        assert summary == "Updated memory: User prefers Python and PostgreSQL."
        mock_client.responses.create.assert_called_once()
        kwargs = mock_client.responses.create.call_args[1]
        assert kwargs["model"] == "gpt-6-luna"
        assert kwargs["max_output_tokens"] == 512
        assert kwargs["reasoning"] == {"effort": "low"}
        assert len(kwargs["input"]) == 1
        assert "User works in software engineering." in kwargs["input"][0]["content"]
        assert "I work with Python." in kwargs["input"][0]["content"]


# ==============================================================================
# 5. Error Handling & Mapping
# ==============================================================================

def test_map_api_error_authentication_401():
    """Verify 401 AuthenticationError maps to sanitized 502 error."""
    req = MagicMock()
    exc = openai.AuthenticationError(
        message="Incorrect API key provided: sk-invalid...",
        response=MagicMock(status_code=401),
        body=None,
    )
    mapped = _map_api_error(exc)
    assert mapped.status_code == 502
    assert "sk-invalid" not in mapped.message
    assert "rejected the API key" in mapped.message


def test_map_api_error_permission_denied_403():
    """Verify 403 PermissionDeniedError maps to 502."""
    exc = openai.PermissionDeniedError(
        message="Project permission denied",
        response=MagicMock(status_code=403),
        body=None,
    )
    mapped = _map_api_error(exc)
    assert mapped.status_code == 502
    assert "rejected the API key" in mapped.message


def test_map_api_error_rate_limit_429():
    """Verify 429 RateLimitError maps to 429."""
    exc = openai.RateLimitError(
        message="Rate limit exceeded",
        response=MagicMock(status_code=429),
        body=None,
    )
    mapped = _map_api_error(exc)
    assert mapped.status_code == 429
    assert "rate limit" in mapped.message.lower()


def test_map_api_error_timeout_504():
    """Verify APITimeoutError maps to 504."""
    exc = openai.APITimeoutError(request=MagicMock())
    mapped = _map_api_error(exc)
    assert mapped.status_code == 504
    assert "timed out" in mapped.message.lower()


def test_map_api_error_network_connection_502():
    """Verify APIConnectionError maps to 502."""
    exc = openai.APIConnectionError(request=MagicMock())
    mapped = _map_api_error(exc)
    assert mapped.status_code == 502
    assert "network" in mapped.message.lower() or "connectivity" in mapped.message.lower()


def test_map_api_error_internal_server_error_502():
    """Verify 500/503 InternalServerError maps to 502."""
    exc = openai.InternalServerError(
        message="Internal server error",
        response=MagicMock(status_code=500),
        body=None,
    )
    mapped = _map_api_error(exc)
    assert mapped.status_code == 502
    assert "temporarily unavailable" in mapped.message.lower()


# ==============================================================================
# 6. Bounded Retries for Transient Errors vs Permanent Failures
# ==============================================================================

@pytest.mark.asyncio
async def test_bounded_retries_transient_connection_error():
    """Verify transient APIConnectionError is retried up to bounded max_retries."""
    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.output_text = "Recovered after retry"

    # First attempt fails with connection error, second attempt succeeds
    mock_client.responses.create.side_effect = [
        openai.APIConnectionError(request=MagicMock()),
        mock_resp,
    ]

    with patch("asyncio.sleep", new_callable=AsyncMock):  # Speed up test
        result = await _call_responses_api_with_retry(
            mock_client,
            model="gpt-6-luna",
            input_messages=[{"role": "user", "content": "Hi"}],
            instructions="Inst",
            max_output_tokens=100,
            max_retries=2,
        )

    assert result == "Recovered after retry"
    assert mock_client.responses.create.call_count == 2


@pytest.mark.asyncio
async def test_no_retries_on_permanent_auth_error():
    """Verify permanent AuthenticationError is NOT retried at all."""
    mock_client = AsyncMock()
    mock_client.responses.create.side_effect = openai.AuthenticationError(
        message="Invalid key",
        response=MagicMock(status_code=401),
        body=None,
    )

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        with pytest.raises(LLMProviderError) as exc_info:
            await _call_responses_api_with_retry(
                mock_client,
                model="gpt-6-luna",
                input_messages=[{"role": "user", "content": "Hi"}],
                instructions="Inst",
                max_output_tokens=100,
                max_retries=2,
            )

        assert exc_info.value.status_code == 502
        # Crucial check: exactly 1 attempt, zero retries, no sleep called!
        assert mock_client.responses.create.call_count == 1
        mock_sleep.assert_not_called()


@pytest.mark.asyncio
async def test_empty_response_raises_provider_error():
    """Verify empty response text raises LLMProviderError."""
    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.output_text = "   "
    mock_client.responses.create.return_value = mock_resp

    with pytest.raises(LLMProviderError) as exc_info:
        await _call_responses_api_with_retry(
            mock_client,
            model="gpt-6-luna",
            input_messages=[{"role": "user", "content": "Hi"}],
            instructions="Inst",
            max_output_tokens=100,
        )
    assert exc_info.value.status_code == 502
    assert "empty response" in exc_info.value.message.lower()


# ==============================================================================
# 7. No Silent Gemini Fallback
# ==============================================================================

@pytest.mark.asyncio
async def test_no_silent_gemini_fallback_on_failure():
    """Verify that when OpenAI fails, it NEVER attempts to fall back to Gemini."""
    mock_client = AsyncMock()
    mock_client.responses.create.side_effect = openai.RateLimitError(
        message="Rate limit",
        response=MagicMock(status_code=429),
        body=None,
    )

    # Patch gemini module to ensure it is never invoked
    with patch("app.gemini.generate_reply") as mock_gemini_gen, \
         patch("app.openai_client.get_client", return_value=mock_client):

        with pytest.raises(LLMProviderError) as exc_info:
            await generate_reply([{"role": "user", "content": "Test"}], SYSTEM_INSTRUCTION)

        assert exc_info.value.status_code == 429
        # Gemini must NEVER be called
        mock_gemini_gen.assert_not_called()

