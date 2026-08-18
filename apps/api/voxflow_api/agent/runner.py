"""Agent runner — owns the conversation loop, tool execution, and LangSmith tracing.

This is the brain of the voice agent. It:
- Resolves tenant-specific dynamic persona & prompt guidelines
- Holds the per-call message history
- Calls the LLM with system prompt + history + tool schemas
- Executes tool calls via the dispatcher
- Traces execution to LangSmith with multi-tenant metadata
- Returns the final reply text + the list of actions taken
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..voice.pipeline import CallSession

from ..config import get_settings
from ..db import Tenant, session_scope
from ..llm import get_llm
from ..llm.base import ChatTurn, LLMProvider
from ..logging import get_logger
from .prompts import build_system_prompt, build_tenant_prompt
from .tools import TOOL_DEFINITIONS, execute_tool

try:
    from langsmith import traceable
except ImportError:  # pragma: no cover
    def traceable(*args, **kwargs):
        def decorator(fn):
            return fn
        return decorator


log = get_logger(__name__)

# Configure LangSmith environment if keys are configured
_settings = get_settings()
if _settings.langsmith_tracing or _settings.langsmith_api_key or os.environ.get("LANGSMITH_API_KEY"):
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    if _settings.langsmith_api_key:
        os.environ["LANGCHAIN_API_KEY"] = _settings.langsmith_api_key
    if _settings.langsmith_project:
        os.environ["LANGCHAIN_PROJECT"] = _settings.langsmith_project
    if _settings.langsmith_endpoint:
        os.environ["LANGCHAIN_ENDPOINT"] = _settings.langsmith_endpoint


@dataclass
class AgentTurnResult:
    reply: str
    actions: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    finish_reason: str = "stop"


class AgentRunner:
    def __init__(self, llm: LLMProvider | None = None) -> None:
        self._llm = llm
        self.max_iterations = 5  # safety: prevent infinite tool loops
        self._prompt_cache: dict[str, tuple[float, str]] = {}

    def _resolve_tenant_prompt(self, tenant_id: str) -> str:
        """Fetch and compile the dynamic system prompt for this tenant with caching."""
        now = time.time()
        cached = self._prompt_cache.get(tenant_id)
        if cached and now - cached[0] < 60:  # cache for 60 seconds
            return cached[1]

        try:
            with session_scope() as db:
                tenant = db.get(Tenant, tenant_id)
                if tenant:
                    prompt = build_tenant_prompt(tenant)
                    self._prompt_cache[tenant_id] = (now, prompt)
                    return prompt
        except Exception as e:
            log.warning("runner.tenant_prompt_fallback", tenant_id=tenant_id, error=str(e))

        s = get_settings()
        prompt = build_system_prompt(business_name=s.business_name)
        self._prompt_cache[tenant_id] = (now, prompt)
        return prompt

    @staticmethod
    def _call_context(session: CallSession) -> str:
        """Facts about THIS call, as a system message."""
        return (
            "CALL CONTEXT (facts about this call — not spoken by the caller):\n"
            f"- Tenant ID: {session.tenant_id}\n"
            f"- Caller's number: {session.caller_phone or 'withheld / not available'}\n"
            f"- Caller's company: {session.company_name or 'unidentified'}\n"
            f"- Verified so far: {'YES' if session.verified else 'NO — disclose no order details yet'}\n"
            f"- Verification attempts used: {session.verify_attempts} of 3\n"
            "Pass the caller's number to lookup_supplier exactly as written above. "
            "If it says withheld, do not invent one — ask the caller for their company name "
            "and call lookup_supplier with the name instead."
        )

    def _history(self, session: CallSession) -> list[ChatTurn]:
        """Convert transcript -> ChatTurns for the LLM. Injects tenant-specific prompt."""
        system_prompt = self._resolve_tenant_prompt(session.tenant_id)
        turns: list[ChatTurn] = [
            ChatTurn(role="system", content=system_prompt),
            ChatTurn(role="system", content=self._call_context(session)),
        ]
        for t in session.transcript:
            role = "user" if t.role == "caller" else "assistant"
            turns.append(ChatTurn(role=role, content=t.text))
        return turns

    @traceable(name="voxflow_voice_turn", run_type="chain")
    async def handle_turn(self, session: CallSession, user_text: str) -> AgentTurnResult:
        llm = self._llm or get_llm()
        history = self._history(session)
        actions: list[dict[str, Any]] = []
        all_tool_calls: list[dict[str, Any]] = []

        for iteration in range(self.max_iterations):
            t0 = time.time()
            resp = await llm.chat(history, tools=TOOL_DEFINITIONS)
            log.info(
                "llm.turn",
                iter=iteration,
                tenant=session.tenant_id,
                provider=resp.provider,
                model=resp.model,
                finish=resp.finish_reason,
                tools=len(resp.tool_calls or []),
                ms=int((time.time() - t0) * 1000),
            )

            # Add assistant message
            history.append(
                ChatTurn(
                    role="assistant",
                    content=resp.content or "",
                    tool_calls=resp.tool_calls or None,
                )
            )

            tool_calls = resp.tool_calls or []
            if not tool_calls:
                return AgentTurnResult(
                    reply=resp.content.strip() if resp.content else "...",
                    actions=actions,
                    tool_calls=all_tool_calls,
                    finish_reason=resp.finish_reason,
                )

            # Execute each tool call
            for tc in tool_calls:
                fn = tc.get("function", {}) if isinstance(tc, dict) else {}
                name = fn.get("name", "")
                raw_args = fn.get("arguments", "{}")
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                except json.JSONDecodeError:
                    args = {}
                tool_call_id = tc.get("id") or f"call_{iteration}_{len(actions)}"

                log.info("tool.call", tenant=session.tenant_id, name=name, args=args)
                t_tool = time.time()
                result = await execute_tool(name, args, session)
                log.info("timing.tool", name=name, ms=int((time.time() - t_tool) * 1000))
                actions.append(
                    {
                        "name": name,
                        "args": args,
                        "result": result,
                        "at": time.time(),
                    }
                )
                all_tool_calls.append({"name": name, "args": args})

                history.append(
                    ChatTurn(
                        role="tool",
                        name=name,
                        tool_call_id=tool_call_id,
                        content=json.dumps(result, default=str),
                    )
                )

        # Hit max iterations — return whatever the last assistant message was.
        last_assistant = next((m.content for m in reversed(history) if m.role == "assistant" and m.content), "")
        return AgentTurnResult(
            reply=last_assistant.strip() or "मुझे एक पल रुकने दीजिए, मैं इसे चेक करके बताती हूँ।",
            actions=actions,
            tool_calls=all_tool_calls,
            finish_reason="max_iterations",
        )
