"""Groq — free tier, ultra-fast inference. https://console.groq.com"""

from __future__ import annotations

import httpx

from .base import ChatTurn, LLMProvider, LLMResponse
from ..logging import get_logger


log = get_logger(__name__)


class GroqProvider(LLMProvider):
    name = "groq"

    def __init__(self, api_key: str, model: str, temperature: float = 0.2, max_tokens: int = 512) -> None:
        if not api_key:
            raise ValueError("GROQ_API_KEY is required when LLM_PROVIDER=groq")
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._base = "https://api.groq.com/openai/v1"

    async def chat(
        self,
        messages: list[ChatTurn],
        *,
        tools: list[dict] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload: dict = {
            "model": self.model,
            "messages": [self._turn_to_dict(m) for m in messages],
            "temperature": temperature if temperature is not None else self.temperature,
            "max_completion_tokens": max_tokens or self.max_tokens,
        }
        # GPT-OSS consumes completion tokens for reasoning before producing its
        # customer-facing answer. Keep reasoning fast and private for voice turns.
        if self.model.startswith("openai/gpt-oss-"):
            payload["reasoning_effort"] = "low"
            payload["include_reasoning"] = False
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        import asyncio

        retries = 3
        backoff = 1.0
        data = None
        for attempt in range(retries):
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(f"{self._base}/chat/completions", json=payload, headers=headers)
                if r.status_code == 429 and attempt < retries - 1:
                    retry_after = r.headers.get("retry-after")
                    wait_time = float(retry_after) if retry_after else backoff * (2 ** attempt)
                    log.warning("groq.rate_limited", attempt=attempt, wait_s=round(wait_time, 2), model=self.model)
                    await asyncio.sleep(wait_time)
                    continue
                if r.status_code != 200:
                    log.error(
                        "groq.error_response",
                        status=r.status_code,
                        model=self.model,
                        message_count=len(messages),
                        tool_count=len(tools or []),
                    )
                r.raise_for_status()
                data = r.json()
                break

        if data is None:
            raise RuntimeError("groq_completion_failed")

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
        if not self.api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(
                    f"{self._base}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
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
