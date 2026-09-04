"""Groq — free tier, ultra-fast inference. https://console.groq.com"""

from __future__ import annotations

import asyncio
import random
from typing import Any

import httpx

from .base import ChatTurn, LLMProvider, LLMResponse
from ..config import get_settings
from ..logging import get_logger


log = get_logger(__name__)


class GroqProvider(LLMProvider):
    name = "groq"

    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 512,
        fallback_model: str | None = None,
        fallback_models: list[str] | str | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("GROQ_API_KEY is required when LLM_PROVIDER=groq")
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Build prioritized fallback cascade excluding primary model
        settings = get_settings()
        raw_fallbacks: list[str] = []
        if fallback_models:
            if isinstance(fallback_models, str):
                raw_fallbacks.extend([m.strip() for m in fallback_models.split(",") if m.strip()])
            else:
                raw_fallbacks.extend(fallback_models)
        elif fallback_model:
            raw_fallbacks.append(fallback_model)
        else:
            configured_cascade = getattr(settings, "groq_fallback_models", "")
            if configured_cascade:
                raw_fallbacks.extend([m.strip() for m in configured_cascade.split(",") if m.strip()])
            elif settings.groq_fallback_model:
                raw_fallbacks.append(settings.groq_fallback_model)

        self.fallback_models: list[str] = [m for m in raw_fallbacks if m and m != self.model]
        # Backwards compatibility property
        self.fallback_model = self.fallback_models[0] if self.fallback_models else None
        self._base = "https://api.groq.com/openai/v1"
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        """Get or initialize the persistent pooled HTTP client for low-latency turns."""
        if self._client is None or getattr(self._client, "is_closed", False) is True:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=10.0),
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20, keepalive_expiry=30.0),
            )
        return self._client

    async def close(self) -> None:
        """Close pooled HTTP connections."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def chat(
        self,
        messages: list[ChatTurn],
        *,
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        effective_temp = temperature if temperature is not None else self.temperature
        effective_tokens = max_tokens or self.max_tokens
        msg_dicts = [self._turn_to_dict(m) for m in messages]

        # Primary model attempt loop with jittered backoff
        data = await self._execute_chat_with_retry(
            model=self.model,
            messages=msg_dicts,
            headers=headers,
            temperature=effective_temp,
            max_tokens=effective_tokens,
            tools=tools,
        )

        # If primary model failed due to rate limits or capacity, iterate through fallback cascade
        if data is None and self.fallback_models:
            for candidate_fallback in self.fallback_models:
                log.warning(
                    "groq.fallback_model_activated",
                    primary_model=self.model,
                    fallback_model=candidate_fallback,
                )
                data = await self._execute_chat_with_retry(
                    model=candidate_fallback,
                    messages=msg_dicts,
                    headers=headers,
                    temperature=effective_temp,
                    max_tokens=effective_tokens,
                    tools=tools,
                    max_retries=1,
                )
                if data is not None:
                    break

        if data is None:
            raise RuntimeError("groq_completion_failed")

        choice = data["choices"][0]
        msg = choice.get("message", {})
        used_model = data.get("model", self.model)
        return LLMResponse(
            content=msg.get("content", "") or "",
            tool_calls=msg.get("tool_calls", []) or [],
            finish_reason=choice.get("finish_reason", "stop"),
            provider=self.name,
            model=used_model,
        )

    async def _execute_chat_with_retry(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        headers: dict[str, str],
        temperature: float,
        max_tokens: int,
        tools: list[dict[str, Any]] | None = None,
        max_retries: int = 3,
    ) -> dict[str, Any] | None:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_completion_tokens": max_tokens,
        }
        if model.startswith("openai/gpt-oss-"):
            payload["reasoning_effort"] = "low"
            payload["include_reasoning"] = False
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        backoff = 1.0
        settings = get_settings()
        client = self._get_client()

        for attempt in range(max_retries):
            try:
                r = await client.post(f"{self._base}/chat/completions", json=payload, headers=headers)
            except (httpx.ConnectError, httpx.ReadTimeout) as conn_err:
                log.warning("groq.connection_error", attempt=attempt, error=str(conn_err), model=model)
                if attempt < max_retries - 1:
                    await asyncio.sleep(backoff * (attempt + 1))
                    continue
                return None

            if r.status_code in (429, 503) and attempt < max_retries - 1:
                retry_after = r.headers.get("retry-after")
                requested_wait = float(retry_after) if retry_after else backoff * (2**attempt)
                jitter = random.uniform(0.85, 1.15)
                wait_time = min(requested_wait * jitter, settings.groq_max_retry_after_seconds)
                log.warning(
                    "groq.rate_limited",
                    attempt=attempt,
                    wait_s=round(wait_time, 2),
                    requested_wait_s=round(requested_wait, 2),
                    model=model,
                )
                await asyncio.sleep(wait_time)
                continue

            if r.status_code != 200:
                log.error(
                    "groq.error_response",
                    status=r.status_code,
                    model=model,
                    message_count=len(messages),
                    tool_count=len(tools or []),
                )
                if r.status_code in (429, 503):
                    return None
                r.raise_for_status()

            return r.json()

        return None

    async def health(self) -> bool:
        if not self.api_key:
            return False
        try:
            client = self._get_client()
            r = await client.get(
                f"{self._base}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            return r.status_code == 200
        except Exception:
            return False

    def _turn_to_dict(self, m: ChatTurn) -> dict[str, Any]:
        d: dict[str, Any] = {"role": m.role, "content": m.content}
        if m.name:
            d["name"] = m.name
        if m.tool_call_id:
            d["tool_call_id"] = m.tool_call_id
        if m.tool_calls:
            d["tool_calls"] = m.tool_calls
        return d

