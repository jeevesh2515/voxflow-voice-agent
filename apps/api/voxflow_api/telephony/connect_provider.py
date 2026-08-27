"""Amazon Connect provider implementation.

Amazon Connect executes telephony through AWS Contact Flows + AWS Lambda.
Unlike Twilio/Telnyx WebSockets, Amazon Connect performs speech recognition
and speech synthesis natively via AWS (Amazon Transcribe / Lex and Amazon Polly).
AWS Lambda communicates with VoxFlow via signed REST API turns.
"""

from __future__ import annotations

import hashlib
import hmac
import math
import os
import time
from typing import Any

from fastapi import Request

from ..config import get_settings
from ..logging import get_logger
from .base import IncomingCall, MediaStart, TelephonyProvider

log = get_logger(__name__)

_MAX_SIGNATURE_AGE_SECONDS = 300


def _is_production(settings: Any) -> bool:
    """Best-effort production detection for the fail-closed secret gate.

    An explicit ``ENVIRONMENT``/``APP_ENV``/Sentry environment always wins.
    If none is set, also treat a non-SQLite ``DATABASE_URL`` as production:
    per SETUP.md, SQLite is only ever used for local development and the
    isolated test suite, so a deployment an operator forgot to label with
    ``ENVIRONMENT=production`` but pointed at a real Postgres database must
    still fail closed rather than silently accepting unsigned requests.
    """
    environment = (
        os.environ.get("ENVIRONMENT")
        or os.environ.get("APP_ENV")
        or settings.sentry_environment
    )
    if environment.strip().lower() in {"prod", "production"}:
        return True
    database_url = getattr(settings, "database_url", "") or ""
    return bool(database_url) and not database_url.startswith("sqlite")


class ConnectProvider(TelephonyProvider):
    name = "connect"

    def validate_webhook(
        self, request: Request, form: dict[str, Any], path: str,
    ) -> bool:
        """Verify the Lambda HMAC over timestamp, path, and exact request bytes."""
        settings = get_settings()
        secret = (
            getattr(settings, "connect_lambda_secret", "")
            or settings.provider_callback_shared_secret
        )
        production = _is_production(settings)
        if production and not secret:
            log.error("connect.signing_secret_missing")
            return False
        if not secret:
            return True
        if not production and not settings.provider_callback_validate_signature:
            return True

        signature = request.headers.get("x-voxflow-signature", "")
        timestamp = request.headers.get("x-voxflow-timestamp", "")
        raw_body = getattr(request.state, "connect_raw_body", None)
        if not signature or not timestamp or not isinstance(raw_body, bytes):
            return False

        try:
            sent_at = float(timestamp)
        except (TypeError, ValueError):
            return False
        if not math.isfinite(sent_at):
            return False

        max_age = max(
            1,
            min(
                int(settings.provider_callback_max_age_seconds),
                _MAX_SIGNATURE_AGE_SECONDS,
            ),
        )
        age = abs(time.time() - sent_at)
        if age > max_age:
            log.warning("connect.stale_request", age=round(age, 3))
            return False

        message = (
            timestamp.encode("utf-8")
            + b":"
            + path.encode("utf-8")
            + b":"
            + raw_body
        )
        expected = hmac.new(
            secret.encode("utf-8"),
            message,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def parse_incoming_call(self, form: dict[str, Any]) -> IncomingCall:
        return IncomingCall(
            call_sid=str(form.get("contact_id") or form.get("ContactId") or ""),
            caller_phone=str(form.get("customer_phone") or form.get("CustomerEndpoint", {}).get("Address", "")),
            to_number=str(form.get("system_phone") or form.get("SystemEndpoint", {}).get("Address", "")),
            provider=self.name,
            raw=form,
        )

    def generate_connect_response(self, ws_host: str, ws_path: str) -> str:
        return '{"status": "ok", "provider": "connect"}'

    def content_type(self) -> str:
        return "application/json"

    def parse_media_start(self, msg: dict[str, Any]) -> MediaStart:
        return MediaStart(
            stream_sid=msg.get("stream_sid", ""),
            call_sid=msg.get("contact_id", ""),
            provider=self.name,
            raw=msg,
        )

    def decode_audio_frame(self, msg: dict[str, Any]) -> bytes:
        return b""

    def encode_audio_frame(self, mulaw_chunk: bytes, stream_sid: str) -> str:
        return '{"event": "media"}'

    def encode_clear(self, stream_sid: str) -> str:
        return '{"event": "clear"}'
