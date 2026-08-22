"""Resilience tests for interactive free-tier LLM availability."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from voxflow_api.agent.runner import AgentRunner


class FailingProvider:
    name = "test-provider"

    async def chat(self, *args, **kwargs):
        raise RuntimeError("rate limited")


@pytest.mark.asyncio
async def test_agent_returns_no_action_fallback_when_model_is_unavailable():
    session = SimpleNamespace(
        tenant_id="varun",
        transcript=[],
        caller_phone="",
        company_name="",
        verified=False,
        verify_attempts=0,
        language="hi",
    )
    runner = AgentRunner(llm=FailingProvider())
    runner._resolve_tenant_prompt = lambda tenant_id: "test prompt"  # type: ignore[method-assign]

    result = await runner.handle_turn(session, "Check stock of cartons")

    assert result.finish_reason == "provider_unavailable"
    assert "कोई कार्रवाई नहीं की गई" in result.reply
    assert result.actions == []
    assert result.tool_calls == []


@pytest.mark.asyncio
async def test_english_provider_fallback_remains_explicitly_non_activating():
    session = SimpleNamespace(
        tenant_id="varun",
        transcript=[],
        caller_phone="",
        company_name="",
        verified=False,
        verify_attempts=0,
        language="en",
    )
    runner = AgentRunner(llm=FailingProvider())
    runner._resolve_tenant_prompt = lambda tenant_id: "test prompt"  # type: ignore[method-assign]

    result = await runner.handle_turn(session, "Check stock")

    assert result.finish_reason == "provider_unavailable"
    assert result.reply == "The demonstration assistant is temporarily busy. Please try again shortly; no action was taken."
    assert result.actions == []
