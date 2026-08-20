"""Dial webhook verification and sandbox-only lifecycle normalization for Day 33.

This module contains provider protocol details only. It never resolves a tenant,
creates a provider operation, or issues a Dial request; Day 32 reconciliation
remains the single durable application boundary.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from fastapi import Request

from ..config import get_settings


AdapterDisposition = Literal["apply", "ping", "ignored"]
ProviderEventType = Literal[
    "request_accepted",
    "connected",
    "ended",
    "recording_ready",
    "business_outcome",
]


class DialCallbackError(ValueError):
    """Structured, safe error raised before any Day 32 callback mutation."""

    def __init__(
        self,
        code: str,
        *,
        status_code: int,
        provider_event_id: str | None = None,
        provider_event_type: str | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code
        self.provider_event_id = provider_event_id
        self.provider_event_type = provider_event_type


@dataclass(frozen=True)
class DialNormalizedCallback:
    """Provider-neutral event that may be passed to the Day 32 ledger."""

    provider_event_id: str
    provider_call_id: str
    event_type: ProviderEventType
    occurred_at: datetime
    outcome: str | None


@dataclass(frozen=True)
class DialCallbackParseResult:
    """Verified Dial callback outcome, including safe non-application cases."""

    provider_event_id: str
    provider_event_type: str
    disposition: AdapterDisposition
    reason_code: str | None
    normalized: DialNormalizedCallback | None


def dial_callback_allowed_tenant_ids() -> tuple[str, ...]:
    """Return the deliberate adapter application allow-list, without defaults."""

    raw = get_settings().dial_callback_allowed_tenants
    return tuple(sorted({value.strip() for value in raw.split(",") if value.strip()}))


def _configured_signing_secrets() -> tuple[str, ...]:
    """Return active and optional previous secret for a controlled rotation overlap."""

    raw = get_settings().dial_callback_signing_secrets
    return tuple(value.strip() for value in raw.split(",") if value.strip())


def _signature_parts(value: str, *, event_id: str | None, event_type: str | None) -> tuple[str, str]:
    components: dict[str, str] = {}
    for item in value.split(","):
        name, separator, component = item.strip().partition("=")
        if not separator or not name or not component or name in components:
            raise DialCallbackError(
                "invalid_dial_signature_header",
                status_code=403,
                provider_event_id=event_id,
                provider_event_type=event_type,
            )
        components[name] = component
    timestamp = components.get("t", "")
    digest = components.get("v1", "")
    if not timestamp or not digest:
        raise DialCallbackError(
            "invalid_dial_signature_header",
            status_code=403,
            provider_event_id=event_id,
            provider_event_type=event_type,
        )
    return timestamp, digest


def _parse_occurred_at(value: object, *, event_id: str, event_type: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise DialCallbackError(
            "invalid_dial_event_timestamp",
            status_code=422,
            provider_event_id=event_id,
            provider_event_type=event_type,
        )
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DialCallbackError(
            "invalid_dial_event_timestamp",
            status_code=422,
            provider_event_id=event_id,
            provider_event_type=event_type,
        ) from exc
    if result.tzinfo is None:
        raise DialCallbackError(
            "invalid_dial_event_timestamp",
            status_code=422,
            provider_event_id=event_id,
            provider_event_type=event_type,
        )
    return result.astimezone(timezone.utc)


def _outcome(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    return normalized


def _ignore(event_id: str, event_type: str, reason_code: str) -> DialCallbackParseResult:
    return DialCallbackParseResult(
        provider_event_id=event_id,
        provider_event_type=event_type,
        disposition="ignored",
        reason_code=reason_code,
        normalized=None,
    )


def _require_call_data(payload: dict[str, object], *, event_id: str, event_type: str) -> tuple[str, dict[str, object]]:
    data = payload.get("data")
    if not isinstance(data, dict):
        raise DialCallbackError(
            "invalid_dial_event_data",
            status_code=422,
            provider_event_id=event_id,
            provider_event_type=event_type,
        )
    call_id = data.get("callId")
    if not isinstance(call_id, str) or not call_id:
        raise DialCallbackError(
            "invalid_dial_call_id",
            status_code=422,
            provider_event_id=event_id,
            provider_event_type=event_type,
        )
    return call_id, data


def _normalise_verified_event(payload: dict[str, object], event_id: str, event_type: str) -> DialCallbackParseResult:
    occurred_at = _parse_occurred_at(payload.get("createdAt"), event_id=event_id, event_type=event_type)
    if event_type == "webhook.ping":
        return DialCallbackParseResult(
            provider_event_id=event_id,
            provider_event_type=event_type,
            disposition="ping",
            reason_code=None,
            normalized=None,
        )
    if event_type not in {"call.status_changed", "call.ended"}:
        return _ignore(event_id, event_type, "unsupported_dial_event_type")

    call_id, data = _require_call_data(payload, event_id=event_id, event_type=event_type)
    if data.get("direction") != "outbound":
        return _ignore(event_id, event_type, "non_outbound_dial_event")

    if event_type == "call.status_changed":
        status = data.get("status")
        state = status.get("state") if isinstance(status, dict) else None
        event_mapping: dict[str, ProviderEventType] = {
            "Queued": "request_accepted",
            "In-Progress": "connected",
            "Terminated": "ended",
        }
        normalized_event_type = event_mapping.get(state) if isinstance(state, str) else None
        if normalized_event_type is None:
            return _ignore(event_id, event_type, "unsupported_dial_call_state")
        return DialCallbackParseResult(
            provider_event_id=event_id,
            provider_event_type=event_type,
            disposition="apply",
            reason_code=None,
            normalized=DialNormalizedCallback(
                provider_event_id=event_id,
                provider_call_id=call_id,
                event_type=normalized_event_type,
                occurred_at=occurred_at,
                outcome=_outcome(data.get("terminationType")) if normalized_event_type == "ended" else None,
            ),
        )

    outcome = "cancelled" if data.get("canceled") is True else _outcome(data.get("status"))
    return DialCallbackParseResult(
        provider_event_id=event_id,
        provider_event_type=event_type,
        disposition="apply",
        reason_code=None,
        normalized=DialNormalizedCallback(
            provider_event_id=event_id,
            provider_call_id=call_id,
            event_type="ended",
            occurred_at=occurred_at,
            outcome=outcome,
        ),
    )


def verify_and_normalise_dial_callback(request: Request, raw_body: bytes) -> DialCallbackParseResult:
    """Fail closed, verify Dial's raw-body HMAC, and normalize a safe subset.

    The adapter intentionally checks its enablement and sandbox configuration
    before reading untrusted JSON. It may accept a previous signing secret during
    a deliberate rotation overlap, but it never exposes which secret matched.
    """

    settings = get_settings()
    header_event_id = request.headers.get("X-Dial-Event-ID") or None
    header_event_type = request.headers.get("X-Dial-Event-Type") or None
    if not settings.dial_callback_adapter_enabled:
        raise DialCallbackError(
            "dial_callback_adapter_disabled",
            status_code=503,
            provider_event_id=header_event_id,
            provider_event_type=header_event_type,
        )
    if not settings.dial_callback_sandbox_mode:
        raise DialCallbackError(
            "dial_callback_sandbox_mode_required",
            status_code=503,
            provider_event_id=header_event_id,
            provider_event_type=header_event_type,
        )
    secrets = _configured_signing_secrets()
    if not secrets:
        raise DialCallbackError(
            "dial_callback_not_configured",
            status_code=503,
            provider_event_id=header_event_id,
            provider_event_type=header_event_type,
        )

    signature_header = request.headers.get("X-Dial-Signature", "")
    timestamp, supplied_digest = _signature_parts(
        signature_header,
        event_id=header_event_id,
        event_type=header_event_type,
    )
    try:
        sent_at = int(timestamp)
    except ValueError as exc:
        raise DialCallbackError(
            "invalid_dial_signature_timestamp",
            status_code=403,
            provider_event_id=header_event_id,
            provider_event_type=header_event_type,
        ) from exc
    now = int(datetime.now(timezone.utc).timestamp())
    if abs(now - sent_at) > settings.dial_callback_max_age_seconds:
        raise DialCallbackError(
            "stale_dial_signature_timestamp",
            status_code=403,
            provider_event_id=header_event_id,
            provider_event_type=header_event_type,
        )
    message = timestamp.encode("ascii") + b"." + raw_body
    verified = any(
        hmac.compare_digest(
            hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest(),
            supplied_digest,
        )
        for secret in secrets
    )
    if not verified:
        raise DialCallbackError(
            "invalid_dial_signature",
            status_code=403,
            provider_event_id=header_event_id,
            provider_event_type=header_event_type,
        )

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise DialCallbackError(
            "invalid_dial_json",
            status_code=422,
            provider_event_id=header_event_id,
            provider_event_type=header_event_type,
        ) from exc
    if not isinstance(payload, dict):
        raise DialCallbackError(
            "invalid_dial_event_envelope",
            status_code=422,
            provider_event_id=header_event_id,
            provider_event_type=header_event_type,
        )
    event_id = payload.get("id")
    event_type = payload.get("type")
    if not isinstance(event_id, str) or not event_id or not isinstance(event_type, str) or not event_type:
        raise DialCallbackError(
            "invalid_dial_event_envelope",
            status_code=422,
            provider_event_id=header_event_id,
            provider_event_type=header_event_type,
        )
    if header_event_id != event_id or header_event_type != event_type:
        raise DialCallbackError(
            "dial_event_header_mismatch",
            status_code=403,
            provider_event_id=event_id,
            provider_event_type=event_type,
        )
    if payload.get("object") != "event":
        raise DialCallbackError(
            "invalid_dial_event_envelope",
            status_code=422,
            provider_event_id=event_id,
            provider_event_type=event_type,
        )
    return _normalise_verified_event(payload, event_id, event_type)
