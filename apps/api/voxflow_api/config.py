"""Centralised settings — read from .env, validated at import time."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic import field_validator
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
    # Default to "groq" for cloud production and sub-200ms voice turns.
    llm_provider: LLMProvider = "groq"
    llm_temperature: float = 0.2
    # GPT-OSS reasoning requires room for both low-effort reasoning and the
    # customer-facing final answer. Override with LLM_MAX_TOKENS if needed.
    llm_max_tokens: int = 4096

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    groq_api_key: str = ""
    # `openai/gpt-oss-20b` is the account-available, tool-capable Groq model
    # verified for the production credential. Override with GROQ_MODEL when needed.
    groq_model: str = "openai/gpt-oss-20b"
    # Bound provider-advised retry delays in the interactive free-tier demo.
    # After the short retry budget is exhausted, the agent returns a safe
    # no-action fallback rather than leaving a browser session stalled.
    groq_max_retry_after_seconds: float = 5.0

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
    database_url: str = "sqlite:////tmp/voxflow-data/voxflow.db"
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_publishable_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwks_url: str = ""
    supabase_use_pooler: bool = False
    # Production Postgres is migration-managed. In ``auto`` mode only SQLite
    # bootstraps tables at process start, keeping cold starts free of recurring
    # create_all/compatibility DDL. Use ``always`` only for controlled legacy
    # bootstrap, or ``skip`` after an explicit migration-managed confirmation.
    db_schema_bootstrap_mode: Literal["auto", "always", "skip"] = "auto"

    # ----- Tenant identity and authorization -----
    # Supabase proves identity, while the tenant_members table controls access.
    # Platform-admin IDs are intentionally empty by default, so tenant creation
    # is fail-closed until an operator explicitly configures an owner identity.
    tenant_authorization_enforced: bool = True
    platform_admin_user_ids: str = ""
    demo_mode_enabled: bool = True
    demo_tenant_id: str = "varun"

    # ----- Public form protection and optional monitoring -----
    # When no Turnstile secret exists, the local/demo form path explicitly
    # reports protection as unavailable. When configured, invalid or missing
    # tokens fail closed at the backend verification endpoint.
    turnstile_secret_key: str = ""
    turnstile_expected_hostname: str = ""
    sentry_dsn: str = ""
    sentry_environment: str = "development"
    sentry_traces_sample_rate: float = 0.0

    @field_validator("database_url", mode="before")
    @classmethod
    def sanitize_database_url(cls, v: str | None) -> str:
        if not v or not isinstance(v, str) or v.strip() == "":
            return "sqlite:////tmp/voxflow-data/voxflow.db"
        val = v.strip()
        # If user mistakenly set DATABASE_URL to an http/https URL (e.g. Supabase project URL)
        if val.startswith("http://") or val.startswith("https://"):
            return "sqlite:////tmp/voxflow-data/voxflow.db"
        # SQLAlchemy 2.0 requires postgresql:// instead of legacy postgres://
        if val.startswith("postgres://"):
            return val.replace("postgres://", "postgresql://", 1)
        return val

    public_base_url: str = ""
    default_tenant_id: str = "varun"
    telephony_provider: str = "connect"

    # ----- Amazon Connect (AWS Voice Contact Center) -----
    connect_lambda_secret: str = ""
    connect_instance_id: str = "voxflow-agent"
    connect_contact_flow_id: str = ""
    connect_phone_number: str = "+442046404552"
    connect_region: str = "us-west-2"

    # ----- Dial (AI Telephony & Outbound Voice Agent) -----
    dial_api_key: str = ""
    dial_phone_number: str = "+14845499931"

    # ----- Durable campaign worker rollout (Day 29) -----
    # Global kill switch stays false until the canary process is independently deployed.
    durable_campaign_worker_enabled: bool = False
    durable_campaign_canary_tenants: str = ""
    durable_campaign_dry_run: bool = True
    durable_campaign_max_in_flight_per_tenant: int = 1

    # ----- Provider callback lifecycle (Day 32) -----
    # Public callback ingestion fails closed when signature verification is on
    # and no shared secret has been configured for the provider adapter.
    provider_callback_shared_secret: str = ""
    provider_callback_validate_signature: bool = True
    provider_callback_max_age_seconds: int = 300

    # ----- Dial sandbox callback adapter (Day 33) -----
    # This provider-specific adapter stays off until fixture certification and an
    # explicit sandbox tenant allow-list are both in place. It is independent of
    # the campaign-worker kill switch, which must remain false for Day 33.
    dial_callback_adapter_enabled: bool = False
    dial_callback_sandbox_mode: bool = True
    dial_callback_allowed_tenants: str = ""
    # Current and previous webhook secrets may be supplied comma-delimited for a
    # short, deliberate signing-secret rotation overlap. Blank always fails closed.
    dial_callback_signing_secrets: str = ""
    dial_callback_max_age_seconds: int = 300

    # ----- Day 35 controlled-pilot readiness -----
    # Admission is fail-closed: a tenant needs an approved, unexpired pilot
    # configuration *and* an explicit environment allow-list before a campaign
    # target can pass the pilot gate. This setting never starts a worker.
    pilot_readiness_enforced: bool = True
    pilot_readiness_approved_tenants: str = ""

    # ----- Day 36 evidence-led pilot operations -----
    # A ready Day 35 configuration is not enough to dispatch. This default-on
    # hold-point gate requires a fresh persisted decision for the current pilot
    # version and same approved micro-cohort. It never enables a worker or
    # approves a tenant by itself.
    pilot_operations_evidence_enforced: bool = True

    # ----- Day 34 durable operational side-effect worker -----
    # Separate from the campaign worker. It remains disabled and dry-run by
    # default so a deployment cannot send messages, post webhooks, write sheets,
    # fetch recordings, or invoke Gmail as an implicit API-process task.
    durable_side_effects_worker_enabled: bool = False
    durable_side_effects_dry_run: bool = True
    durable_side_effects_allowed_tenants: str = ""
    durable_side_effects_max_concurrency: int = 1
    durable_side_effects_poll_interval_seconds: float = 2.0

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
    google_sheet_email_tab: str = "Email Log"
    sheets_enabled: bool = False

    # ----- Email Summarizer & Gmail -----
    gmail_user_email: str = ""
    gmail_app_password: str = ""
    gmail_imap_server: str = "imap.gmail.com"
    gmail_imap_port: int = 993
    email_summarizer_enabled: bool = True
    email_summarizer_interval_seconds: int = 28800  # 8 hours = 3 times daily

    # ----- Persistence & Storage -----
    data_dir: str = "./data"
    sheets_retry_interval: int = 60
    log_retention_days: int = 30
    db_backup_keep_days: int = 7

    # ----- LangSmith (LLM Observability & Evals) -----
    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "voxflow-production"
    langsmith_endpoint: str = "https://api.smith.langchain.com"

    # ----- Logging -----
    log_level: str = "INFO"

    # ----- Business -----
    business_name: str = "VoxFlow"
    business_timezone: str = "Asia/Kolkata"

    @property
    def durable_side_effects_allowed_tenant_ids(self) -> tuple[str, ...]:
        """Parse the explicit tenant allow-list for the Day 34 worker pool."""

        return tuple(
            tenant_id.strip()
            for tenant_id in self.durable_side_effects_allowed_tenants.split(",")
            if tenant_id.strip()
        )

    @property
    def durable_campaign_canary_tenant_ids(self) -> tuple[str, ...]:
        """Parse the explicit tenant allow-list used by the campaign worker."""

        return tuple(
            tenant_id.strip()
            for tenant_id in self.durable_campaign_canary_tenants.split(",")
            if tenant_id.strip()
        )

    @property
    def pilot_readiness_approved_tenant_ids(self) -> tuple[str, ...]:
        """Parse the tenant IDs deliberately approved for a future pilot gate."""

        return tuple(
            tenant_id.strip()
            for tenant_id in self.pilot_readiness_approved_tenants.split(",")
            if tenant_id.strip()
        )

    @property
    def platform_admin_user_id_set(self) -> tuple[str, ...]:
        """Parse the explicit Supabase subject allow-list for platform admins."""

        return tuple(
            user_id.strip()
            for user_id in self.platform_admin_user_ids.split(",")
            if user_id.strip()
        )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]

    @property
    def resolved_data_dir(self) -> str:
        d = self.data_dir
        try:
            os.makedirs(d, exist_ok=True)
            return d
        except (OSError, PermissionError):
            fallback = os.path.abspath("./data")
            os.makedirs(fallback, exist_ok=True)
            return fallback


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
