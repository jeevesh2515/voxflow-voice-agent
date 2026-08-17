"""Centralised settings — read from .env, validated at import time."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


LLMProvider = Literal["ollama", "groq", "openrouter"]
STTProvider = Literal["local", "groq"]


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
    groq_model: str = "openai/gpt-oss-120b"

    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.1-8b-instruct:free"

    # ----- Voice -----
    # "groq"  = Groq whisper-large-v3-turbo, server-side (~200-400ms). Default.
    # "local" = faster-whisper on this box (~1.5-3s, needs requirements-local.txt).
    stt_provider: STTProvider = "groq"
    groq_stt_model: str = "whisper-large-v3-turbo"

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
    supabase_publishable_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwks_url: str = ""
    supabase_use_pooler: bool = False

    # ----- Twilio -----
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    # Optional Twilio API Key credentials (safer than Account SID/Auth Token for
    # CLI tools, SDKs, and REST client calls that do NOT need webhook validation).
    # Leave blank to use Account SID + Auth Token (default; required for webhooks).
    # To generate: Twilio Console → Account → API keys & tokens → Create API key.
    twilio_api_key: str = ""
    twilio_api_secret: str = ""
    # Public https base URL of THIS backend, e.g. https://voxflow-api.up.railway.app
    # Used to build the <Stream> URL in TwiML and to validate webhook signatures.
    public_base_url: str = ""
    # Reject unsigned/forged webhook requests. Keep true in production.
    twilio_validate_signature: bool = True
    # Default Twilio trial phone number for Voice & SMS dispatch
    twilio_phone_number: str = "+447460041934"
    # Default Twilio WhatsApp Sandbox number (format: whatsapp:+14155238886)
    twilio_whatsapp_number: str = "whatsapp:+14155238886"
    # Tenant used when an inbound number isn't mapped in tenant_phone_numbers.
    default_tenant_id: str = "varun"

    # ----- Google Sheets (call-outcome log) -----
    # Paste the full service-account JSON as a single-line env var, OR set
    # google_service_account_file to a path on disk. JSON wins if both are set.
    google_service_account_json: str = ""
    google_service_account_file: str = ""
    # The spreadsheet ID from its URL:
    # docs.google.com/spreadsheets/d/<THIS_PART>/edit
    google_sheet_id: str = ""
    # Tab name inside that spreadsheet.
    google_sheet_tab: str = "Call Log"
    sheets_enabled: bool = False

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
