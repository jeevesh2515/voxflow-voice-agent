"""Centralised settings — read from .env, validated at import time."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


LLMProvider = Literal["ollama", "groq", "openrouter"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ----- LLM -----
    llm_provider: LLMProvider = "ollama"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 512

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"

    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.1-8b-instruct:free"

    # ----- Voice -----
    whisper_model_size: str = "base"
    whisper_device: str = "auto"
    whisper_compute_type: str = "int8"

    tts_voice_hi: str = "hi-IN-SwaraNeural"
    tts_voice_en: str = "en-IN-NeerjaNeural"
    tts_default_lang: Literal["hi", "en"] = "hi"

    # ----- API -----
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_cors_origins: str = "http://localhost:3000"

    # ----- Database & Supabase -----
    database_url: str = "sqlite:///./voxflow.db"
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # ----- Logging -----
    log_level: str = "INFO"

    # ----- Business -----
    business_name: str = "VoxFlow"
    business_timezone: str = "Asia/Kolkata"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
