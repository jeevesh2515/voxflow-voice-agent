"""Telnyx provider implementation — TeXML voice webhook + WebSocket media.

Telnyx Call Control v2 uses:
  - TeXML (TwiML-compatible XML) for voice webhook responses
  - WebSocket streaming for bidirectional audio (similar to Twilio Media Streams)
  - HMAC-SHA256 webhook signature verification using the account's public key

Audio format: 8 kHz μ-law mono (same as Twilio), delivered as base64 in JSON
WebSocket frames. Our existing codec utilities (mulaw_to_pcm, pcm_to_mulaw,
resample_8k_to_16k) work identically.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from fastapi import Request

from ..config import get_settings
from ..logging import get_logger
from .base import IncomingCall, MediaStart, TelephonyProvider

log = get_logger(__name__)


class TelnyxProvider(TelephonyProvider):
    name = "telnyx"

    # ---------- Webhook ----------

    def validate_webhook(
        self, request: Request, form: dict[str, Any], path: str,
    ) -> bool:
        """Verify Telnyx webhook signature.

        Telnyx signs webhooks with an HMAC-SHA256 using the account's signing
        secret.  The signature is in the ``telnyx-signature-ed25519`` header and
        the timestamp in ``telnyx-timestamp``.  For simplicity we also support
        the v1 HMAC path: ``x-telnyx-signature`` + ``x-telnyx-timestamp``.
        """
        s = get_settings()
        if not s.telnyx_validate_signature:
            return True

        signing_secret = s.telnyx_api_secret
        if not signing_secret:
            log.warning("telnyx.signature_skipped", reason="no_signing_secret")
            return True  # permissive when unconfigured (dev mode)

        # Telnyx v2 webhook verification
        timestamp = (
            request.headers.get("telnyx-timestamp")
            or request.headers.get("x-telnyx-timestamp", "")
        )
        signature = (
            request.headers.get("telnyx-signature-ed25519")
            or request.headers.get("x-telnyx-signature", "")
        )

        if not timestamp or not signature:
            return False

        # Protect against replay attacks — reject if older than 5 minutes
        try:
            ts = int(timestamp)
            if abs(time.time() - ts) > 300:
                log.warning("telnyx.stale_webhook", age_seconds=abs(time.time() - ts))
                return False
        except (ValueError, TypeError):
            return False

        # Build the signed payload: timestamp + "." + raw body
        # For JSON webhooks, we reconstruct from form data
        body = json.dumps(form, separators=(",", ":"), sort_keys=True)
        signed_payload = f"{timestamp}.{body}"

        expected = hmac.new(
            signing_secret.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    def parse_incoming_call(self, form: dict[str, Any]) -> IncomingCall:
        """Extract call metadata from Telnyx webhook payload.

        Telnyx Call Control v2 sends JSON with nested ``data.payload``:
        {
          "data": {
            "event_type": "call.initiated",
            "payload": {
              "call_control_id": "...",
              "call_leg_id": "...",
              "call_session_id": "...",
              "from": "+1234567890",
              "to": "+0987654321",
              ...
            }
          }
        }

        For TeXML apps, the webhook is form-encoded (like Twilio):
        CallSid, From, To, etc.
        """
        # TeXML mode (form-encoded, TwiML-compatible)
        if "CallSid" in form:
            return IncomingCall(
                call_sid=form.get("CallSid", ""),
                caller_phone=form.get("From", ""),
                to_number=form.get("To", ""),
                provider=self.name,
                raw=form,
            )

        # Call Control v2 mode (JSON)
        data = form.get("data", {})
        payload = data.get("payload", {})
        return IncomingCall(
            call_sid=payload.get("call_control_id", payload.get("call_session_id", "")),
            caller_phone=payload.get("from", ""),
            to_number=payload.get("to", ""),
            provider=self.name,
            raw=form,
        )

    def generate_connect_response(self, ws_host: str, ws_path: str) -> str:
        """Return TeXML response to connect audio streaming.

        TeXML is TwiML-compatible — Telnyx accepts the same XML verbs.
        The <Stream> element opens a WebSocket back to our server.
        """
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
        """Parse the start event from a Telnyx WebSocket stream.

        Telnyx Media Streaming sends the same event structure as Twilio:
        {
          "event": "start",
          "start": {
            "streamSid": "...",
            "callSid": "...",
            ...
          }
        }
        """
        start = msg.get("start", {})
        return MediaStart(
            stream_sid=start.get("streamSid", start.get("stream_id", "")),
            call_sid=start.get("callSid", start.get("call_control_id", "")),
            provider=self.name,
            raw=start,
        )

    def decode_audio_frame(self, msg: dict[str, Any]) -> bytes:
        """Decode one inbound audio frame.

        Telnyx streams audio in the same format as Twilio:
        {"event": "media", "media": {"payload": "<base64 mulaw>"}}
        """
        payload = msg.get("media", {}).get("payload", "")
        if not payload:
            return b""
        return base64.b64decode(payload)

    def encode_audio_frame(self, mulaw_chunk: bytes, stream_sid: str) -> str:
        """Encode one outbound audio frame for Telnyx WebSocket."""
        payload = base64.b64encode(mulaw_chunk).decode("utf-8")
        return json.dumps({
            "event": "media",
            "streamSid": stream_sid,
            "media": {"payload": payload},
        })

    def encode_clear(self, stream_sid: str) -> str:
        """Send a clear event to flush Telnyx's audio buffer (barge-in)."""
        return json.dumps({"event": "clear", "streamSid": stream_sid})
