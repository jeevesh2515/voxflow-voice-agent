"""Optional privacy-scrubbed error-monitoring integration."""
from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from .config import get_settings
from .logging import get_logger


log = get_logger(__name__)
_SENSITIVE_KEY = re.compile(
    r"(?:authorization|cookie|token|secret|password|phone|email|ip|remote_addr|recording|transcript|body|message|text|prompt|recipient|caller|subject|note|content|payload)",
    re.IGNORECASE,
)
_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")


def _scrub_text(value: str) -> str:
    cleaned = _EMAIL.sub("[redacted-email]", value)
    cleaned = _PHONE.sub("[redacted-phone]", cleaned)
    return cleaned[:256]


def scrub_value(value: Any, *, key: str = "") -> Any:
    """Recursively remove direct identifiers and raw operational content."""

    if _SENSITIVE_KEY.search(key):
        return "[redacted]"
    if isinstance(value, Mapping):
        return {str(item_key): scrub_value(item_value, key=str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, (list, tuple)):
        return [scrub_value(item) for item in value[:20]]
    if isinstance(value, str):
        return _scrub_text(value)
    return value


def scrub_sentry_event(event: dict[str, Any], hint: dict[str, Any] | None = None) -> dict[str, Any]:
    """Scrub a capture event before it leaves the VoxFlow process."""

    sanitized = scrub_value(event)
    request = sanitized.get("request") if isinstance(sanitized, dict) else None
    if isinstance(request, dict):
        request.pop("data", None)
        request.pop("cookies", None)
        request.pop("env", None)
        request["headers"] = {"redacted": "[redacted]"}
        request["url"] = "[redacted-url]"
    if isinstance(sanitized, dict):
        sanitized.pop("user", None)
        sanitized.pop("extra", None)
        sanitized.pop("breadcrumbs", None)
    return sanitized


def init_error_monitoring() -> bool:
    """Initialize Sentry only when explicitly configured; otherwise stay inert."""

    settings = get_settings()
    if not settings.sentry_dsn:
        log.info("monitoring.disabled", reason="sentry_dsn_not_configured")
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
    except ImportError:
        log.warning("monitoring.disabled", reason="sentry_sdk_not_installed")
        return False

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        integrations=[FastApiIntegration()],
        send_default_pii=False,
        traces_sample_rate=max(0.0, min(settings.sentry_traces_sample_rate, 1.0)),
        before_send=scrub_sentry_event,
        before_breadcrumb=lambda breadcrumb, hint: scrub_value(breadcrumb),
    )
    log.info("monitoring.enabled", environment=settings.sentry_environment)
    return True
