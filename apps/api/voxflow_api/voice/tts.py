"""Text-to-speech using Microsoft Edge TTS (free, no key, supports Hindi)."""

from __future__ import annotations

import asyncio
import io
from dataclasses import dataclass

import edge_tts

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

    def synth_sync(self, text: str, lang_hint: str | None = None) -> TTSResult:
        return asyncio.run(self.synth(text, lang_hint))
