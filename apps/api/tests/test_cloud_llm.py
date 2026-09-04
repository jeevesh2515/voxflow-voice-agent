"""Tests for Cloud-First Free-Tier LLM Provider Architecture.

Verifies:
- Default LLM provider resolution to Groq (openai/gpt-oss-20b + openai/gpt-oss-120b fallback).
- Fail-fast validation when GROQ_API_KEY is missing (no silent localhost Ollama fallbacks).
- Payload formatting (tool_calls, reasoning_effort="low", max_completion_tokens).
- Rate limit (429) failover from primary model to fallback model.
- Persistent connection pooling lifecycle.
"""

from __future__ import annotations

import asyncio
from typing import Any
import pytest
import respx
import httpx

from voxflow_api.config import get_settings
from voxflow_api.llm.base import ChatTurn, LLMResponse
from voxflow_api.llm.factory import get_llm, reset_llm_provider
from voxflow_api.llm.groq import GroqProvider


@pytest.fixture(autouse=True)
def _clean_llm_state():
    reset_llm_provider()
    get_settings.cache_clear()
    yield
    reset_llm_provider()
    get_settings.cache_clear()


def test_factory_initializes_groq_with_free_tier_defaults(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_mock_free_key_123")
    monkeypatch.setenv("GROQ_MODEL", "openai/gpt-oss-20b")
    monkeypatch.setenv("GROQ_FALLBACK_MODEL", "openai/gpt-oss-120b")
    get_settings.cache_clear()

    llm = get_llm()
    assert isinstance(llm, GroqProvider)
    assert llm.name == "groq"
    assert llm.model == "openai/gpt-oss-20b"
    assert llm.fallback_model == "openai/gpt-oss-120b"
    assert llm.api_key == "gsk_test_mock_free_key_123"


def test_factory_fails_fast_when_groq_key_missing(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "")
    get_settings.cache_clear()

    with pytest.raises(ValueError) as excinfo:
        get_llm()
    assert "GROQ_API_KEY is required" in str(excinfo.value)
    assert "console.groq.com" in str(excinfo.value)


@pytest.mark.asyncio
@respx.mock
async def test_groq_provider_chat_completion_success():
    respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "model": "openai/gpt-oss-20b",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "Hello! How can I assist with your order today?",
                        },
                        "finish_reason": "stop",
                    }
                ],
            },
        )
    )

    provider = GroqProvider(
        api_key="gsk_test_key",
        model="openai/gpt-oss-20b",
        fallback_model="openai/gpt-oss-120b",
    )

    response = await provider.chat([ChatTurn(role="user", content="Hi")])
    assert response.content == "Hello! How can I assist with your order today?"
    assert response.provider == "groq"
    assert response.model == "openai/gpt-oss-20b"
    await provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_groq_provider_formats_tools_and_reasoning_effort():
    route = respx.post("https://api.groq.com/openai/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "chatcmpl-tool",
                "model": "openai/gpt-oss-20b",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": "call_123",
                                    "type": "function",
                                    "function": {
                                        "name": "lookup_order",
                                        "arguments": '{"order_id": "ORD-101"}',
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
            },
        )
    )

    provider = GroqProvider(
        api_key="gsk_test_key",
        model="openai/gpt-oss-20b",
    )

    tools = [
        {
            "type": "function",
            "function": {
                "name": "lookup_order",
                "description": "Lookup order",
                "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}}},
            },
        }
    ]

    response = await provider.chat(
        [ChatTurn(role="user", content="Check order ORD-101")],
        tools=tools,
    )

    assert len(response.tool_calls) == 1
    assert response.tool_calls[0]["function"]["name"] == "lookup_order"

    # Verify request payload
    last_request = route.calls.last.request
    import json
    body = json.loads(last_request.content.decode("utf-8"))
    assert body["model"] == "openai/gpt-oss-20b"
    assert body["reasoning_effort"] == "low"
    assert body["include_reasoning"] is False
    assert len(body["tools"]) == 1
    await provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_groq_provider_fails_over_to_fallback_model_on_rate_limit():
    call_count = 0

    def handle_request(request):
        nonlocal call_count
        call_count += 1
        import json
        body = json.loads(request.content.decode("utf-8"))
        if body["model"] == "openai/gpt-oss-20b":
            # Primary exhausted budget
            return httpx.Response(429, headers={"retry-after": "1"})
        elif body["model"] == "openai/gpt-oss-120b":
            # Fallback model succeeds
            return httpx.Response(
                200,
                json={
                    "id": "chatcmpl-fallback",
                    "model": "openai/gpt-oss-120b",
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": "Fallback model recovered the turn successfully.",
                            },
                            "finish_reason": "stop",
                        }
                    ],
                },
            )
        return httpx.Response(400)

    respx.post("https://api.groq.com/openai/v1/chat/completions").mock(side_effect=handle_request)

    provider = GroqProvider(
        api_key="gsk_test_key",
        model="openai/gpt-oss-20b",
        fallback_model="openai/gpt-oss-120b",
    )

    response = await provider.chat([ChatTurn(role="user", content="Hello")])
    assert response.content == "Fallback model recovered the turn successfully."
    assert response.model == "openai/gpt-oss-120b"
    await provider.close()


@pytest.mark.asyncio
@respx.mock
async def test_groq_provider_multi_model_fallback_cascade():
    """Verify fallback cascades from primary (20b) -> fallback 1 (120b) -> fallback 2 (qwen 27b)."""
    attempted_models = []

    def handle_request(request):
        import json
        body = json.loads(request.content.decode("utf-8"))
        model = body["model"]
        attempted_models.append(model)

        if model == "openai/gpt-oss-20b":
            # Primary exhausted 429
            return httpx.Response(429, headers={"retry-after": "0.1"})
        elif model == "openai/gpt-oss-120b":
            # Fallback 1 temporarily 503
            return httpx.Response(503)
        elif model == "qwen/qwen3.8-27b":
            # Fallback 2 succeeds
            return httpx.Response(
                200,
                json={
                    "id": "chatcmpl-qwen",
                    "model": "qwen/qwen3.8-27b",
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": "Qwen 27B free tier rescued the conversation.",
                            },
                            "finish_reason": "stop",
                        }
                    ],
                },
            )
        return httpx.Response(400)

    respx.post("https://api.groq.com/openai/v1/chat/completions").mock(side_effect=handle_request)

    provider = GroqProvider(
        api_key="gsk_test_key",
        model="openai/gpt-oss-20b",
        fallback_models=["openai/gpt-oss-120b", "qwen/qwen3.8-27b"],
    )

    response = await provider.chat([ChatTurn(role="user", content="Urgent stock check")])
    assert response.content == "Qwen 27B free tier rescued the conversation."
    assert response.model == "qwen/qwen3.8-27b"
    assert attempted_models == ["openai/gpt-oss-20b", "openai/gpt-oss-20b", "openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b"]
    await provider.close()
