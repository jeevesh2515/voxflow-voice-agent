"""Abstract base for telephony providers (Twilio, Telnyx, Amazon Connect).

Each provider must implement:
  - webhook signature verification
  - incoming call metadata parsing
  - audio stream connect response generation (TwiML, TeXML, etc.)
  - WebSocket media frame encoding/decoding
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from fastapi import Request


@dataclass(frozen=True)
class IncomingCall:
    """Normalised metadata extracted from a provider's inbound call webhook."""

    call_sid: str
    caller_phone: str
    to_number: str
    provider: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MediaStart:
    """Normalised metadata from a provider's WebSocket stream-start event."""

    stream_sid: str
    call_sid: str
    provider: str
    raw: dict[str, Any] = field(default_factory=dict)


class TelephonyProvider(ABC):
    """Contract every telephony backend must satisfy."""

    name: str = "base"

    # ---------- Webhook ----------

    @abstractmethod
    def validate_webhook(
        self, request: Request, form: dict[str, Any], path: str,
    ) -> bool:
        """Return True when the inbound webhook request is authentically signed."""

    @abstractmethod
    def parse_incoming_call(self, form: dict[str, Any]) -> IncomingCall:
        """Extract normalised call metadata from the provider's form payload."""

    @abstractmethod
    def generate_connect_response(self, ws_host: str, ws_path: str) -> str:
        """Return provider-specific XML/JSON that tells the provider to open an
        audio WebSocket back to *ws_host/ws_path*."""

    @abstractmethod
    def content_type(self) -> str:
        """MIME type for the connect response (e.g. application/xml)."""

    # ---------- WebSocket media ----------

    @abstractmethod
    def parse_media_start(self, msg: dict[str, Any]) -> MediaStart:
        """Extract stream/call SID from the WebSocket ``start`` event."""

    @abstractmethod
    def decode_audio_frame(self, msg: dict[str, Any]) -> bytes:
        """Return raw μ-law (or PCM) bytes from one inbound media frame."""

    @abstractmethod
    def encode_audio_frame(
        self, mulaw_chunk: bytes, stream_sid: str,
    ) -> str:
        """Return the JSON text to send one outbound audio frame."""

    @abstractmethod
    def encode_clear(self, stream_sid: str) -> str:
        """Return the JSON text to flush/clear the provider's playback buffer
        (barge-in support)."""
