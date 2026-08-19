"""Dial integration for programmatic AI outbound voice calling and unified SMS."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

from ..config import get_settings
from ..logging import get_logger

log = get_logger(__name__)

DIAL_API_BASE = "https://api.getdial.ai"


class DialClient:
    """Async client for Dial API (AI Voice Calling & Messaging)."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def _get_api_key(self) -> str:
        """Resolve API key from settings or ~/.local/share/dial/auth.v1.json."""
        s = get_settings()
        if s.dial_api_key:
            return s.dial_api_key

        env_key = os.environ.get("DIAL_API_KEY")
        if env_key:
            return env_key

        auth_path = os.path.expanduser("~/.local/share/dial/auth.v1.json")
        if os.path.exists(auth_path):
            try:
                with open(auth_path, encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("apiKey") or ""
            except Exception:
                pass
        return ""

    def is_configured(self) -> bool:
        return bool(self._get_api_key())

    async def place_outbound_call(
        self,
        to_number: str,
        instruction: str,
        voice_gender: str = "female",
        language: str | None = None,
        max_duration_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Place an outbound AI voice call to a supplier, distributor, or customer."""
        api_key = self._get_api_key()
        if not api_key:
            log.warning("dial.api_key_missing")
            return {"ok": False, "error": "dial_not_configured", "detail": "DIAL_API_KEY is not set."}

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "to": to_number,
            "outboundInstruction": instruction,
            "voiceGender": voice_gender,
        }
        if language:
            lang_map = {
                "hi": "hi-IN",
                "en": "en-IN",
                "hi-in": "hi-IN",
                "en-in": "en-IN",
                "en-us": "en-US",
                "en-gb": "en-GB",
            }
            payload["language"] = lang_map.get(language.lower(), language)
        if max_duration_seconds:
            payload["maxCallDurationSeconds"] = max_duration_seconds

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(
                    f"{DIAL_API_BASE}/api/v1/calls",
                    headers=headers,
                    json=payload,
                )
                if r.status_code >= 300:
                    log.error("dial.call_placement_failed", status=r.status_code, body=r.text[:300])
                    return {"ok": False, "error": f"http_{r.status_code}", "detail": r.text[:200]}

                data = r.json()
                log.info("dial.call_placed_success", to=to_number, call_id=data.get("call", {}).get("id"))
                return {"ok": True, "call": data.get("call", {})}
        except Exception as e:
            log.error("dial.call_placement_exception", error=str(e))
            return {"ok": False, "error": "exception", "detail": str(e)}

    async def get_call(self, call_id: str) -> dict[str, Any]:
        """Fetch details and transcript for an outbound call."""
        api_key = self._get_api_key()
        if not api_key:
            return {"ok": False, "error": "dial_not_configured"}

        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                r = await client.get(f"{DIAL_API_BASE}/api/v1/calls/{call_id}", headers=headers)
                if r.status_code >= 300:
                    return {"ok": False, "error": f"http_{r.status_code}"}
                return {"ok": True, "call": r.json().get("call", {})}
        except Exception as e:
            return {"ok": False, "error": "exception", "detail": str(e)}

    async def list_calls(self, limit: int = 20) -> list[dict[str, Any]]:
        """List recent calls on the account."""
        api_key = self._get_api_key()
        if not api_key:
            return []

        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                r = await client.get(f"{DIAL_API_BASE}/api/v1/calls?limit={limit}", headers=headers)
                if r.status_code >= 300:
                    return []
                return r.json().get("calls", [])
        except Exception:
            return []


_dial_client: DialClient | None = None


def get_dial_client() -> DialClient:
    global _dial_client
    if _dial_client is None:
        _dial_client = DialClient()
    return _dial_client
