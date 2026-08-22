"""Amazon Connect provider implementation.

Amazon Connect executes telephony through AWS Contact Flows + AWS Lambda.
Unlike Twilio/Telnyx WebSockets, Amazon Connect performs speech recognition
and speech synthesis natively via AWS (Amazon Transcribe / Lex and Amazon Polly).
AWS Lambda communicates with VoxFlow via signed REST API turns.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any

from fastapi import Request

from ..config import get_settings
from ..logging import get_logger
from .base import IncomingCall, MediaStart, TelephonyProvider

log = get_logger(__name__)


class ConnectProvider(TelephonyProvider):
    name = "connect"

    def validate_webhook(
        self, request: Request, form: dict[str, Any], path: str,
    ) -> bool:
        """Verify HMAC signature sent by VoxFlow AWS Lambda bridge."""
        s = get_settings()
        secret = getattr(s, "connect_lambda_secret", "") or s.provider_callback_shared_secret
        if not secret:
            return True  # Dev mode / unconfigured

        signature = request.headers.get("x-voxflow-signature", "")
        timestamp = request.headers.get("x-voxflow-timestamp", "")
        if not signature or not timestamp:
            return False

        try:
            ts = float(timestamp)
            if abs(time.time() - ts) > 300:
                log.warning("connect.stale_request", age=abs(time.time() - ts))
                return False
        except (ValueError, TypeError):
            return False

        # Verify signature over timestamp + path
        expected = hmac.new(
            secret.encode("utf-8"),
            f"{timestamp}:{path}".encode("utf-8"),
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
