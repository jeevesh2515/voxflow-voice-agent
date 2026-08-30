"""Optional privacy-scrubbed error-monitoring and product-analytics integration."""
from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
import re
from typing import Any

from .config import get_settings
from .logging import get_logger
from .services.pin_security import redact_pin_text


log = get_logger(__name__)
_SENSITIVE_KEY = re.compile(
    r"(?:authorization|cookie|token|secret|password|pin|phone|email|ip|remote_addr|recording|transcript|body|message|text|prompt|recipient|caller|subject|note|content|payload|order|customer|address|name)",
    re.IGNORECASE,
)
_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")


def _scrub_text(value: str) -> str:
    """Remove direct identifiers from free text and bound its length.

    PIN redaction is applied last and deliberately fails closed: any bare 4-8
    digit run is rewritten, so a spoken verification PIN cannot reach a vendor
    even inside an unstructured exception message. Bare year-like numbers are
    rewritten as collateral, which is accepted — structured timestamps are
    carried in their own event fields.
    """

    cleaned = _EMAIL.sub("[redacted-email]", value)
    cleaned = _PHONE.sub("[redacted-phone]", cleaned)
    cleaned = redact_pin_text(cleaned)
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


REDACTED_MESSAGE = "[redacted-free-text]"


def _scrub_exception_values(exception: Any) -> Any:
    """Keep exception structure, drop every free-text and local-variable field.

    An exception message is arbitrary developer text. In this codebase it can
    embed a caller name interpolated from a call record, and a personal name is
    not regex-detectable the way an email or phone number is. So the message is
    dropped rather than pattern-scrubbed, and stack-frame ``vars`` (which hold
    live PINs, transcripts, and order payloads) go with it. What remains — the
    exception type, module, mechanism, and the file/line/function of every frame
    — is what actually localizes a defect.
    """

    if not isinstance(exception, Mapping):
        return exception
    values = exception.get("values")
    if not isinstance(values, (list, tuple)):
        return exception

    cleaned_values = []
    for entry in values[:20]:
        if not isinstance(entry, Mapping):
            continue
        cleaned: dict[str, Any] = {
            "type": str(entry.get("type") or "")[:128],
            "value": REDACTED_MESSAGE,
        }
        if entry.get("module"):
            cleaned["module"] = str(entry["module"])[:128]
        if entry.get("mechanism"):
            cleaned["mechanism"] = scrub_value(entry["mechanism"])
        stacktrace = entry.get("stacktrace")
        if isinstance(stacktrace, Mapping) and isinstance(stacktrace.get("frames"), (list, tuple)):
            cleaned["stacktrace"] = {
                "frames": [
                    {
                        "filename": str(frame.get("filename") or "")[:256],
                        "function": str(frame.get("function") or "")[:128],
                        "lineno": frame.get("lineno"),
                        "module": str(frame.get("module") or "")[:128],
                    }
                    for frame in stacktrace["frames"][:50]
                    if isinstance(frame, Mapping)
                ]
            }
        cleaned_values.append(cleaned)
    return {"values": cleaned_values}


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
        # Free-text narrative fields cannot be name-scrubbed, so they are dropped.
        if "message" in sanitized:
            sanitized["message"] = REDACTED_MESSAGE
        sanitized.pop("logentry", None)
        if "exception" in sanitized:
            sanitized["exception"] = _scrub_exception_values(event.get("exception"))
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


# --------------------------------------------------------------------------- #
# Day 51 product analytics (PostHog)
# --------------------------------------------------------------------------- #

# Any property name outside this allow-list is dropped rather than scrubbed. An
# allow-list fails closed: a future caller that invents `caller_full_name` sends
# nothing instead of relying on the key regex to catch it.
ANALYTICS_ALLOWED_PROPERTIES = frozenset(
    {
        "action",
        "alert_code",
        "alert_count",
        "call_count",
        "channel",
        "component",
        "duration_ms",
        "error_code",
        "escalation_rate",
        "feature",
        "job_type",
        "language",
        "latency_ms",
        "outcome",
        "page",
        "plan",
        "provider",
        "range_days",
        "resolution_rate",
        "result",
        "role",
        "severity",
        "status",
        "subsystem",
        "surface",
        "time_range",
        "variant",
        "version",
    }
)

_MAX_ANALYTICS_STRING = 64


def hash_tenant_id(tenant_id: str) -> str:
    """Return the vendor-facing tenant label.

    A workspace slug is customer-identifying, so by default it is salted and
    hashed before it leaves the process. Set OBSERVABILITY_HASH_TENANT_IDS=false
    to send the raw ID when a deployment owns its own analytics project.
    """

    settings = get_settings()
    value = (tenant_id or "").strip()
    if not value:
        return ""
    if not settings.observability_hash_tenant_ids:
        return value
    salted = f"{settings.observability_tenant_hash_salt}:{value}".encode("utf-8")
    return f"t_{sha256(salted).hexdigest()[:32]}"


def scrub_analytics_properties(properties: Mapping[str, Any] | None) -> dict[str, Any]:
    """Reduce arbitrary event properties to allow-listed, scrubbed scalars.

    Nested structures (order JSON, transcript arrays, tool-call payloads) are
    rejected outright: a product-analytics event never needs them, and allowing
    them is how raw customer data reaches a third party.
    """

    if not properties:
        return {}
    safe: dict[str, Any] = {}
    for raw_key, raw_value in properties.items():
        key = str(raw_key).strip().lower()
        if key not in ANALYTICS_ALLOWED_PROPERTIES:
            continue
        if isinstance(raw_value, bool) or isinstance(raw_value, (int, float)):
            safe[key] = raw_value
        elif isinstance(raw_value, str):
            cleaned = redact_pin_text(_scrub_text(raw_value))
            safe[key] = cleaned[:_MAX_ANALYTICS_STRING]
        elif raw_value is None:
            safe[key] = None
        # Mappings, lists, and objects are intentionally dropped.
    return safe


_posthog_client: Any | None = None
_posthog_initialized = False


def init_product_analytics() -> bool:
    """Initialize PostHog only when a project key is configured."""

    global _posthog_client, _posthog_initialized
    _posthog_initialized = True
    settings = get_settings()
    if not settings.posthog_api_key:
        log.info("analytics.disabled", reason="posthog_api_key_not_configured")
        _posthog_client = None
        return False
    try:
        from posthog import Posthog
    except ImportError:
        log.warning("analytics.disabled", reason="posthog_not_installed")
        _posthog_client = None
        return False

    _posthog_client = Posthog(
        project_api_key=settings.posthog_api_key,
        host=settings.posthog_host,
        # PostHog's own auto-capture of IPs and person profiles is disabled; the
        # allow-list above is the only data path.
        disable_geoip=True,
    )
    log.info("analytics.enabled", host=settings.posthog_host)
    return True


def capture_event(
    event: str,
    *,
    tenant_id: str = "",
    properties: Mapping[str, Any] | None = None,
) -> bool:
    """Send one scrubbed product-analytics event. Never raises to the caller."""

    if not _posthog_initialized:
        init_product_analytics()
    if _posthog_client is None:
        return False

    name = str(event or "").strip()[:64]
    if not name:
        return False
    safe_properties = scrub_analytics_properties(properties)
    distinct_id = hash_tenant_id(tenant_id) or "anonymous"
    if distinct_id != "anonymous":
        safe_properties["tenant"] = distinct_id
    try:
        _posthog_client.capture(distinct_id=distinct_id, event=name, properties=safe_properties)
        return True
    except Exception as exc:  # pragma: no cover - vendor transport failure
        log.warning("analytics.capture_failed", event=name, error=str(exc))
        return False
