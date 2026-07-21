"""Abstract LLM provider. All three adapters (Ollama, Groq, OpenRouter) implement this."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMResponse:
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    finish_reason: str = "stop"
    provider: str = ""
    model: str = ""


@dataclass
class ChatTurn:
    role: str
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


class LLMProvider(ABC):
    name: str = "base"
    model: str = ""

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatTurn],
        *,
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Send a chat completion request, optionally with tool/function definitions.

        `messages` is a list of ChatTurn. `tools` follows the OpenAI tools spec
        (we normalise across providers so the agent layer is provider-agnostic).
        """
        raise NotImplementedError

    @abstractmethod
    async def health(self) -> bool:
        """True if the provider is reachable and credentials are valid."""
        raise NotImplementedError
