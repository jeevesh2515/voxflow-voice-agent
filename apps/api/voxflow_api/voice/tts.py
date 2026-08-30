"""Text-to-speech using Microsoft Edge TTS (free, no key, supports Hindi)."""

from __future__ import annotations

import asyncio
import io
from dataclasses import dataclass

try:
    import edge_tts
except ModuleNotFoundError:  # optional browser-audio enhancement
    edge_tts = None

from ..config import get_settings
from ..logging import get_logger


log = get_logger(__name__)


@dataclass
class TTSResult:
    audio_bytes: bytes
    mime: str = "audio/mpeg"


class TextToSpeech:
    """Generates MP3 audio for a given text + voice."""

    def __init__(self) -> None:
        s = get_settings()
        self.voice_hi = s.tts_voice_hi
        self.voice_en = s.tts_voice_en
        self.default_lang = s.tts_default_lang

    def pick_voice(self, text: str, lang_hint: str | None = None) -> str:
        """Pick a voice. Heuristic: if text is mostly Devanagari, use Hindi voice."""
        if lang_hint in ("hi", "hindi"):
            return self.voice_hi
        if lang_hint in ("en", "english"):
            return self.voice_en
        # auto-detect
        devanagari = sum(1 for c in text if "\u0900" <= c <= "\u097F")
        return self.voice_hi if devanagari > max(3, len(text) // 10) else self.voice_en

    async def synth(self, text: str, lang_hint: str | None = None) -> TTSResult:
        if edge_tts is None:
            raise RuntimeError("edge-tts is unavailable; browser speech fallback is required")
        voice = self.pick_voice(text, lang_hint)
        communicate = edge_tts.Communicate(text=text, voice=voice, rate="+0%", pitch="+0Hz")
        buf = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        data = buf.getvalue()
        if not data:
            raise RuntimeError("TTS produced empty audio")
        return TTSResult(audio_bytes=data, mime="audio/mpeg")

    async def synth_stream(self, text: str, lang_hint: str | None = None):
        """Yield MP3 chunks as they arrive — first byte in ~150ms, not 300ms.

        Keeps `synth` intact for REST/tests; streaming callers get incremental
        audio without buffering the whole file.
        """

        if edge_tts is None:
            raise RuntimeError("edge-tts is unavailable; browser speech fallback is required")
        if not text or not text.strip():
            return
        voice = self.pick_voice(text, lang_hint)
        communicate = edge_tts.Communicate(text=text, voice=voice, rate="+0%", pitch="+0Hz")
        async for chunk in communicate.stream():
            if chunk["type"] == "audio" and chunk.get("data"):
                yield bytes(chunk["data"])

    def synth_sync(self, text: str, lang_hint: str | None = None) -> TTSResult:
        return asyncio.run(self.synth(text, lang_hint))
