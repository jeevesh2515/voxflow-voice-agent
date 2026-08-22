"""Twilio provider implementation — wraps existing TwiML + Media Streams logic.

This module extracts the Twilio-specific protocol details from routes/twilio.py
into the provider abstraction so that the route handler can be shared (or at
least structurally identical) across providers.
"""

from __future__ import annotations

import base64
import json
from typing import Any

from fastapi import Request

from ..config import get_settings
from ..logging import get_logger
from .base import IncomingCall, MediaStart, TelephonyProvider

log = get_logger(__name__)


class TwilioProvider(TelephonyProvider):
    name = "twilio"

    # ---------- Webhook ----------

    def validate_webhook(
        self, request: Request, form: dict[str, Any], path: str,
    ) -> bool:
        s = get_settings()
        if not s.twilio_validate_signature:
            return True
        if not s.twilio_auth_token:
            log.warning("twilio.signature_skipped", reason="no_auth_token_configured")
            return False

        signature = request.headers.get("X-Twilio-Signature", "")
        if not signature:
            return False

        try:
            from twilio.request_validator import RequestValidator
        except ImportError:
            log.error("twilio.sdk_missing", hint="pip install twilio")
            return False

        base = (s.public_base_url or "").rstrip("/")
        if base:
            url = f"{base}{path}"
        else:
            host = request.headers.get("host", "localhost:8000")
            proto = request.headers.get("x-forwarded-proto", request.url.scheme)
            url = f"{proto}://{host}{path}"

        validator = RequestValidator(s.twilio_auth_token)
        return bool(validator.validate(url, form, signature))

    def parse_incoming_call(self, form: dict[str, Any]) -> IncomingCall:
        return IncomingCall(
            call_sid=form.get("CallSid", ""),
            caller_phone=form.get("From", ""),
            to_number=form.get("To", ""),
            provider=self.name,
            raw=form,
        )

    def generate_connect_response(self, ws_host: str, ws_path: str) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            '  <Say voice="Google.hi-IN-Standard-A">नमस्ते, वॉक्सफ़्लो में आपका स्वागत है।</Say>'
            "  <Connect>"
            f'    <Stream url="wss://{ws_host}{ws_path}" />'
            "  </Connect>"
            "</Response>"
        )

    def content_type(self) -> str:
        return "application/xml"

    # ---------- WebSocket media ----------

    def parse_media_start(self, msg: dict[str, Any]) -> MediaStart:
        start = msg.get("start", {})
        return MediaStart(
            stream_sid=start.get("streamSid", ""),
            call_sid=start.get("callSid", ""),
            provider=self.name,
            raw=start,
        )

    def decode_audio_frame(self, msg: dict[str, Any]) -> bytes:
        payload = msg.get("media", {}).get("payload", "")
        if not payload:
            return b""
        return base64.b64decode(payload)

    def encode_audio_frame(self, mulaw_chunk: bytes, stream_sid: str) -> str:
        payload = base64.b64encode(mulaw_chunk).decode("utf-8")
        return json.dumps({
            "event": "media",
            "streamSid": stream_sid,
            "media": {"payload": payload},
        })

    def encode_clear(self, stream_sid: str) -> str:
        return json.dumps({"event": "clear", "streamSid": stream_sid})
