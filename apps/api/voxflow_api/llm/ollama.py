"""Ollama — local LLM. No API key, no cost, runs on your box.

Uses the OpenAI-compatible endpoint exposed by Ollama (>=0.5.0). That way the
agent layer doesn't care which provider it's talking to.
"""

from __future__ import annotations

import httpx

from .base import ChatTurn, LLMProvider, LLMResponse
from ..logging import get_logger


log = get_logger(__name__)


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, base_url: str, model: str, temperature: float = 0.2, max_tokens: int = 512) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def _url(self) -> str:
        return f"{self.base_url}/v1/chat/completions"

    async def chat(
        self,
        messages: list[ChatTurn],
        *,
        tools: list[dict] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        payload: dict = {
            "model": self.model,
            "messages": [self._turn_to_dict(m) for m in messages],
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(self._url(), json=payload)
            r.raise_for_status()
            data = r.json()

        choice = data["choices"][0]
        msg = choice.get("message", {})
        return LLMResponse(
            content=msg.get("content", "") or "",
            tool_calls=msg.get("tool_calls", []) or [],
            finish_reason=choice.get("finish_reason", "stop"),
            provider=self.name,
            model=self.model,
        )

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    def _turn_to_dict(self, m: ChatTurn) -> dict:
        d: dict = {"role": m.role, "content": m.content}
        if m.name:
            d["name"] = m.name
        if m.tool_call_id:
            d["tool_call_id"] = m.tool_call_id
        if m.tool_calls:
            d["tool_calls"] = m.tool_calls
        return d
