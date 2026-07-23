"""Agent runner — owns the conversation loop and tool execution.

This is the brain of the voice agent. It:
- Holds the per-call message history
- Calls the LLM (pluggable) with the system prompt + history + tool schemas
- Executes tool calls via the dispatcher
- Loops until the LLM produces a final assistant message
- Returns the final reply text + the list of actions taken
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..voice.pipeline import CallSession

from ..config import get_settings
from ..llm import get_llm
from ..llm.base import ChatTurn, LLMProvider
from ..logging import get_logger
from .prompts import build_system_prompt
from .tools import TOOL_DEFINITIONS, execute_tool


log = get_logger(__name__)


@dataclass
class AgentTurnResult:
    reply: str
    actions: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    finish_reason: str = "stop"


class AgentRunner:
    def __init__(self, llm: LLMProvider | None = None) -> None:
        s = get_settings()
        self._llm = llm
        self.system_prompt = build_system_prompt(business_name=s.business_name)
        self.max_iterations = 5  # safety: prevent infinite tool loops

    def _history(self, session: CallSession) -> list[ChatTurn]:
        """Convert transcript -> ChatTurns for the LLM. Skip non-text turns."""
        turns: list[ChatTurn] = [ChatTurn(role="system", content=self.system_prompt)]
        for t in session.transcript:
            role = "user" if t.role == "caller" else "assistant"
            turns.append(ChatTurn(role=role, content=t.text))
        return turns

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

                log.info("tool.call", name=name, args=args)
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
