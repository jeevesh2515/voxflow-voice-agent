"""Provider factory — pick one based on LLM_PROVIDER env."""

from __future__ import annotations

from ..config import get_settings
from .base import LLMProvider
from .groq import GroqProvider
from .ollama import OllamaProvider
from .openrouter import OpenRouterProvider
from ..logging import get_logger


log = get_logger(__name__)


_provider_singleton: LLMProvider | None = None


def get_llm() -> LLMProvider:
    global _provider_singleton
    if _provider_singleton is not None:
        return _provider_singleton

    s = get_settings()
    if s.llm_provider == "ollama":
        _provider_singleton = OllamaProvider(
            base_url=s.ollama_base_url,
            model=s.ollama_model,
            temperature=s.llm_temperature,
            max_tokens=s.llm_max_tokens,
        )
    elif s.llm_provider == "groq":
        _provider_singleton = GroqProvider(
            api_key=s.groq_api_key,
            model=s.groq_model,
            temperature=s.llm_temperature,
            max_tokens=s.llm_max_tokens,
        )
    elif s.llm_provider == "openrouter":
        _provider_singleton = OpenRouterProvider(
            api_key=s.openrouter_api_key,
            model=s.openrouter_model,
            temperature=s.llm_temperature,
            max_tokens=s.llm_max_tokens,
        )
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {s.llm_provider}")

    log.info("llm.provider.initialized", provider=_provider_singleton.name, model=_provider_singleton.model)
    return _provider_singleton
