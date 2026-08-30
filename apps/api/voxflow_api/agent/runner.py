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

import asyncio
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
from ..services.pin_security import redact_pin_data, redact_pin_text, redact_tool_calls_for_trace
from .prompts import build_system_prompt, build_tenant_prompt
from .tools import TOOL_DEFINITIONS, execute_tool, gated_tool_count, tool_definitions_for

try:
    from langsmith import traceable
except ImportError:  # pragma: no cover
    def traceable(*args, **kwargs):
        def decorator(fn):
            return fn
        return decorator


log = get_logger(__name__)


def _redacted_trace_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    """Keep caller credentials and full session transcripts out of LangSmith."""
    session = inputs.get("session")
    return {
        "call_id": redact_pin_text(str(getattr(session, "call_id", ""))),
        "tenant_id": redact_pin_text(str(getattr(session, "tenant_id", ""))),
        "user_text": redact_pin_text(str(inputs.get("user_text", ""))),
    }


def _redacted_trace_outputs(outputs: dict[str, Any]) -> dict[str, Any]:
    """Keep replies, actions, and tool traces PIN-free in LangSmith."""
    redacted = redact_pin_data(outputs)
    return redacted if isinstance(redacted, dict) else {"output": redacted}


def _redact_session_evidence(session: CallSession) -> None:
    """Scrub transient caller/tool data before any caller can persist the session.

    ``route_policy`` holds the session's authorization bindings (the supplier IDs
    that ``verify_caller``/``verify_pin`` succeeded against). A blanket
    ``redact_pin_data`` pass rewrites any 4-8 digit run — including numeric
    supplier IDs — into ``[REDACTED PIN]``, silently unbinding verification
    mid-call: the caller re-verifies every turn and the PIN factor keeps
    disappearing. Binding values are internal identifiers, never caller speech,
    so only free-text attributes are redacted here.
    """
    for turn in getattr(session, "transcript", []):
        turn.text = redact_pin_text(turn.text)
    session.actions = redact_pin_data(getattr(session, "actions", []))
    for attr in ("caller_name", "company_name", "intent", "reason", "solution", "related_order"):
        value = getattr(session, attr, None)
        if isinstance(value, str):
            setattr(session, attr, redact_pin_text(value))


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

    def __post_init__(self) -> None:
        """Make every shared caller-facing result safe, including Connect responses."""
        self.reply = redact_pin_text(self.reply)
        self.actions = redact_pin_data(self.actions)
        self.tool_calls = redact_pin_data(self.tool_calls)


_GLOBAL_PROMPT_CACHE: dict[str, tuple[float, str]] = {}


# Day 54: tools that may run concurrently within one turn. Membership requires
# a tool to be a *pure* read — no session mutation and no authorization state
# change — because `asyncio.gather` gives no ordering guarantee.
# `check_po_status` and `get_order_details` are deliberately excluded even
# though they are reads: both assign `session.related_order`, so running two of
# them concurrently would attach a nondeterministic order to the call's
# escalation audit trail. They stay on the sequential path, where the last call
# in the model's own list wins.
_PARALLEL_SAFE: frozenset[str] = frozenset({
    "check_stock", "get_shipment_status", "verify_po",
})


def clear_tenant_prompt_cache(tenant_id: str | None = None) -> None:
    """Invalidate prompt cache entries for a specific tenant or entirely."""
    global _GLOBAL_PROMPT_CACHE
    if tenant_id:
        prefix = f"{tenant_id}:"
        keys_to_del = [k for k in _GLOBAL_PROMPT_CACHE if k.startswith(prefix)]
        for k in keys_to_del:
            _GLOBAL_PROMPT_CACHE.pop(k, None)
    else:
        _GLOBAL_PROMPT_CACHE.clear()


class AgentRunner:
    def __init__(self, llm: LLMProvider | None = None) -> None:
        self._llm = llm
        self.max_iterations = 5  # safety: prevent infinite tool loops
        self._prompt_cache: dict[str, tuple[float, str]] = _GLOBAL_PROMPT_CACHE

    def _resolve_tenant_prompt(self, tenant_id: str, session_language: str | None = None) -> str:
        """Fetch and compile the dynamic system prompt for this tenant with caching."""
        cache_key = f"{tenant_id}:{session_language or 'default'}"
        now = time.time()
        cached = self._prompt_cache.get(cache_key)
        if cached and now - cached[0] < 60:  # cache for 60 seconds
            return cached[1]

        try:
            with session_scope() as db:
                tenant = db.get(Tenant, tenant_id)
                if tenant:
                    prompt = build_tenant_prompt(tenant, session_language=session_language)
                    self._prompt_cache[cache_key] = (now, prompt)
                    return prompt
        except Exception as e:
            log.warning(
                "runner.tenant_prompt_fallback",
                tenant_id=redact_pin_text(tenant_id),
                error=redact_pin_text(str(e)),
            )

        s = get_settings()
        prompt = build_system_prompt(
            business_name=s.business_name,
            default_language=session_language or "en",
        )
        self._prompt_cache[cache_key] = (now, prompt)
        return prompt

    @staticmethod
    def _call_context(session: CallSession) -> str:
        """Facts about THIS call, as a system message."""
        active_lang = session.language or "en"
        verification_mode = getattr(session, "verification_mode", "standard")
        pin_verified = bool(getattr(session, "pin_verified", False))
        verification_policy = (
            "Enhanced mode: complete knowledge verification and verify the caller PIN before any protected order read or write."
            if verification_mode == "enhanced"
            else "Standard mode: complete knowledge verification before protected reads; caller PIN verification is still required for writes."
        )
        return (
            "CALL CONTEXT (facts about this call — not spoken by the caller):\n"
            f"- Tenant ID: {session.tenant_id}\n"
            f"- Active Conversation Language: {active_lang}\n"
            f"- Caller's number: {session.caller_phone or 'withheld / not available'}\n"
            f"- Caller's company: {session.company_name or 'unidentified'}\n"
            f"- Verified so far: {'YES' if session.verified else 'NO — disclose no order details yet'}\n"
            f"- Inbound verification mode: {verification_mode}\n"
            f"- PIN verified so far: {'YES' if pin_verified else 'NO'}\n"
            f"- Route verification policy: {verification_policy}\n"
            f"- Verification attempts used: {session.verify_attempts} of 3\n"
            "Pass the caller's number to lookup_supplier exactly as written above. "
            "If it says withheld, do not invent one — ask the caller for their company name "
            "and call lookup_supplier with the name instead.\n"
            f"CRITICAL: The caller is in an '{active_lang}' session. Respond in {('English' if active_lang == 'en' else 'Hindi')}."
        )

    def _history(self, session: CallSession) -> list[ChatTurn]:
        """Convert transcript -> ChatTurns for the LLM. Injects tenant-specific prompt."""
        try:
            system_prompt = self._resolve_tenant_prompt(session.tenant_id, session.language)
        except TypeError:
            system_prompt = self._resolve_tenant_prompt(session.tenant_id)

        turns: list[ChatTurn] = [
            ChatTurn(role="system", content=system_prompt),
            ChatTurn(role="system", content=self._call_context(session)),
        ]
        for t in session.transcript:
            role = "user" if t.role == "caller" else "assistant"
            turns.append(ChatTurn(role=role, content=t.text))
        return turns

    @traceable(
        name="voxflow_voice_turn",
        run_type="chain",
        process_inputs=_redacted_trace_inputs,
        process_outputs=_redacted_trace_outputs,
    )
    async def handle_turn(self, session: CallSession, user_text: str) -> AgentTurnResult:
        llm = self._llm or get_llm()
        history = self._history(session)
        actions: list[dict[str, Any]] = []
        all_tool_calls: list[dict[str, Any]] = []

        for iteration in range(self.max_iterations):
            t0 = time.time()
            # Day 54: gated tools cut ~1.5k input tokens before verification.
            gated_tools = tool_definitions_for(session)
            try:
                resp = await llm.chat(history, tools=gated_tools)
            except Exception as exc:
                # Provider availability must not leave a browser simulator turn
                # pending indefinitely. Do not disclose internal provider details
                # and do not synthesize or queue any operational side effect.
                log.warning(
                    "llm.turn_unavailable",
                    tenant=redact_pin_text(session.tenant_id),
                    provider=redact_pin_text(str(getattr(llm, "name", "unknown"))),
                    exception_type=type(exc).__name__,
                )
                _redact_session_evidence(session)
                is_hindi = getattr(session, "language", "en") == "hi"
                return AgentTurnResult(
                    reply=(
                        "माफ़ कीजिए, डेमो सहायक अभी व्यस्त है। कृपया कुछ क्षण बाद फिर कोशिश करें। कोई कार्रवाई नहीं की गई है।"
                        if is_hindi
                        else "The demonstration assistant is temporarily busy. Please try again shortly; no action was taken."
                    ),
                    actions=actions,
                    tool_calls=all_tool_calls,
                    finish_reason="provider_unavailable",
                )
            _redact_session_evidence(session)
            log.info(
                "llm.turn",
                iter=iteration,
                tenant=redact_pin_text(session.tenant_id),
                provider=redact_pin_text(resp.provider),
                model=redact_pin_text(resp.model),
                finish=redact_pin_text(resp.finish_reason),
                tools=len(resp.tool_calls or []),
                gated_tools=gated_tool_count(session),
                ms=int((time.time() - t0) * 1000),
            )

            tool_calls = resp.tool_calls or []
            # Preserve id/type/function.name so the tool-calling protocol
            # round-trips correctly on the next turn; only the arguments
            # string is redacted.
            safe_tool_calls = redact_tool_calls_for_trace(tool_calls)
            history.append(
                ChatTurn(
                    role="assistant",
                    content=redact_pin_text(resp.content or ""),
                    tool_calls=safe_tool_calls or None,
                )
            )

            if not tool_calls:
                return AgentTurnResult(
                    reply=resp.content.strip() if resp.content else "...",
                    actions=actions,
                    tool_calls=all_tool_calls,
                    finish_reason=resp.finish_reason,
                )

            # Execute tool calls — parallel for independent reads (Day 54).
            # Parse first so we can decide parallel vs sequential without
            # re-parsing inside the gather.
            parsed: list[tuple[str, dict[str, Any], str]] = []
            for idx, tc in enumerate(tool_calls):
                fn = tc.get("function", {}) if isinstance(tc, dict) else {}
                name = fn.get("name", "")
                raw_args = fn.get("arguments", "{}")
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                except json.JSONDecodeError:
                    args = {}
                tool_call_id = tc.get("id") or f"call_{iteration}_{idx}"
                parsed.append((name, args, tool_call_id))

            can_parallel = (
                len(parsed) > 1 and all(n in _PARALLEL_SAFE for n, _, _ in parsed)
            )

            if can_parallel:
                # Fire all reads concurrently — each still opens its own
                # async_session_scope, but we overlap network/DB wait.
                t_batch = time.time()

                async def _one(n: str, a: dict[str, Any]) -> Any:
                    return redact_pin_data(await execute_tool(n, a, session))

                # Log batch start once; per-tool timing still emitted below.
                for n, a, _ in parsed:
                    log.info("tool.call", tenant=redact_pin_text(session.tenant_id), name=redact_pin_text(n), args=redact_pin_data(a))

                results = await asyncio.gather(*[_one(n, a) for n, a, _ in parsed])

                for (name, args, tool_call_id), result in zip(parsed, results):
                    _redact_session_evidence(session)
                    safe_args = redact_pin_data(args)
                    actions.append({"name": name, "args": safe_args, "result": result, "at": time.time()})
                    all_tool_calls.append({"name": name, "args": safe_args})
                    history.append(ChatTurn(role="tool", name=name, tool_call_id=tool_call_id, content=json.dumps(result, default=str)))

                log.info("timing.tool_batch", count=len(parsed), ms=int((time.time() - t_batch) * 1000))
            else:
                for name, args, tool_call_id in parsed:
                    safe_args = redact_pin_data(args)
                    log.info("tool.call", tenant=redact_pin_text(session.tenant_id), name=redact_pin_text(name), args=safe_args)
                    t_tool = time.time()
                    result = redact_pin_data(await execute_tool(name, args, session))
                    _redact_session_evidence(session)
                    log.info("timing.tool", name=redact_pin_text(name), ms=int((time.time() - t_tool) * 1000))
                    actions.append({"name": name, "args": safe_args, "result": result, "at": time.time()})
                    all_tool_calls.append({"name": name, "args": safe_args})
                    history.append(ChatTurn(role="tool", name=name, tool_call_id=tool_call_id, content=json.dumps(result, default=str)))

        # Hit max iterations — return whatever the last assistant message was.
        last_assistant = next((m.content for m in reversed(history) if m.role == "assistant" and m.content), "")
        return AgentTurnResult(
            reply=last_assistant.strip() or "मुझे एक पल रुकने दीजिए, मैं इसे चेक करके बताती हूँ।",
            actions=actions,
            tool_calls=all_tool_calls,
            finish_reason="max_iterations",
        )
