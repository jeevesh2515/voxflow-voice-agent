"""Speech-to-text with pluggable providers.

Two backends, selected by `STT_PROVIDER`:

* ``groq``  (default) — Groq's hosted ``whisper-large-v3-turbo``. Runs entirely
  server-side, needs no model files, and returns in roughly 200-400ms. This is
  what production uses: it keeps the container near 250MB and takes seconds of
  dead air off every conversational turn.

* ``local`` — ``faster-whisper`` on this machine. Kept for offline development
  only. It is NOT installed by default; ``pip install -r requirements-local.txt``
  if you want it. A ``base`` model costs ~2GB of RAM and 1.5-3s per utterance on
  a small CPU, which is why it is no longer the default.

Both expose the same synchronous interface, and both are called from a worker
thread by ``VoicePipeline`` — so the blocking HTTP call in the Groq backend
never touches the event loop.
"""

from __future__ import annotations

import io
import wave
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from ..config import get_settings
from ..logging import get_logger


log = get_logger(__name__)

GROQ_TRANSCRIBE_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

# Groq returns language as an English word; the app works in ISO-639-1.
_LANG_MAP = {
    "english": "en",
    "hindi": "hi",
    "urdu": "hi",  # Whisper often tags Hinglish/Urdu-adjacent speech this way
    "nepali": "hi",
    "marathi": "hi",
    "sanskrit": "hi",
}


@dataclass
class Transcription:
    text: str
    language: str
    confidence: float
    duration_sec: float


def pcm_to_wav_bytes(pcm: np.ndarray, sample_rate: int = 16000) -> bytes:
    """Wrap a float32 [-1, 1] mono PCM array in a 16-bit WAV container."""
    if pcm.dtype != np.float32:
        pcm = pcm.astype(np.float32)
    clipped = np.clip(pcm, -1.0, 1.0)
    int16 = (clipped * 32767.0).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(int16.tobytes())
    return buf.getvalue()


def _normalise_language(raw: str | None, fallback: str = "hi") -> str:
    if not raw:
        return fallback
    raw = raw.strip().lower()
    if len(raw) == 2:
        return raw if raw in ("hi", "en") else fallback
    return _LANG_MAP.get(raw, fallback)


class STTBackend(Protocol):
    def transcribe_pcm(
        self, pcm: np.ndarray, sample_rate: int = 16000, language: str | None = None
    ) -> Transcription: ...


# ---------------------------------------------------------------- Groq (cloud)


class GroqSTT:
    """Hosted Whisper via Groq's OpenAI-compatible transcription endpoint."""

    def __init__(self) -> None:
        s = get_settings()
        if not s.groq_api_key:
            log.warning("stt.groq_key_missing", msg="GROQ_API_KEY not set yet. STT calls will check settings dynamically.")
            self._api_key = ""
        else:
            self._api_key = s.groq_api_key
        self._model = s.groq_stt_model
        log.info("stt.ready", provider="groq", model=self._model)

    def transcribe_pcm(
        self, pcm: np.ndarray, sample_rate: int = 16000, language: str | None = None
    ) -> Transcription:
        import httpx

        duration = len(pcm) / float(sample_rate)

        # Whisper rejects sub-100ms clips; VAD noise can produce them.
        if duration < 0.1:
            return Transcription(text="", language=language or "hi", confidence=0.0, duration_sec=duration)

        wav = pcm_to_wav_bytes(pcm, sample_rate)
        data = {"model": self._model, "response_format": "verbose_json", "temperature": "0"}
        if language:
            data["language"] = language

        try:
            r = httpx.post(
                GROQ_TRANSCRIBE_URL,
                headers={"Authorization": f"Bearer {self._api_key}"},
                files={"file": ("audio.wav", wav, "audio/wav")},
                data=data,
                timeout=15.0,
            )
        except Exception as e:
            # A transcription failure must not kill the call — the pipeline
            # treats empty text as "didn't catch that" and the agent re-asks.
            log.error("stt.groq_request_failed", error=str(e))
            return Transcription(text="", language=language or "hi", confidence=0.0, duration_sec=duration)

        if r.status_code >= 300:
            log.error("stt.groq_http_error", status=r.status_code, body=r.text[:200])
            return Transcription(text="", language=language or "hi", confidence=0.0, duration_sec=duration)

        payload = r.json()
        text = (payload.get("text") or "").strip()
        lang = _normalise_language(payload.get("language"), fallback=language or "hi")

        # verbose_json gives per-segment no_speech_prob; mirror the local backend.
        probs = [
            1.0 - seg["no_speech_prob"]
            for seg in payload.get("segments", [])
            if isinstance(seg, dict) and seg.get("no_speech_prob") is not None
        ]
        confidence = float(np.mean(probs)) if probs else (0.9 if text else 0.0)

        return Transcription(text=text, language=lang, confidence=confidence, duration_sec=duration)


# --------------------------------------------------------------- local Whisper


class LocalWhisperSTT:
    """faster-whisper on this machine. Development only — see module docstring."""

    def __init__(self) -> None:
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            raise RuntimeError(
                "STT_PROVIDER=local requires faster-whisper, which is not in the "
                "default requirements. Install it with: "
                "pip install -r requirements-local.txt"
            ) from e

        s = get_settings()
        device = s.whisper_device if s.whisper_device != "auto" else "auto"
        log.info(
            "stt.loading",
            provider="local",
            model=s.whisper_model_size,
            device=device,
            compute_type=s.whisper_compute_type,
        )
        self.model = WhisperModel(
            s.whisper_model_size, device=device, compute_type=s.whisper_compute_type
        )
        log.info("stt.ready", provider="local", model=s.whisper_model_size)

    def transcribe_pcm(
        self, pcm: np.ndarray, sample_rate: int = 16000, language: str | None = None
    ) -> Transcription:
        if pcm.dtype != np.float32:
            pcm = pcm.astype(np.float32)
        duration = len(pcm) / float(sample_rate)

        segments, info = self.model.transcribe(
            pcm,
            language=language,  # None => auto-detect (handles hi/en)
            task="transcribe",
            beam_size=1,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 300},
        )
        text_parts: list[str] = []
        probs: list[float] = []
        for seg in segments:
            text_parts.append(seg.text.strip())
            if seg.no_speech_prob is not None:
                probs.append(1.0 - seg.no_speech_prob)

        return Transcription(
            text=" ".join(t for t in text_parts if t).strip(),
            language=_normalise_language(info.language, fallback=language or "hi"),
            confidence=float(np.mean(probs)) if probs else 0.0,
            duration_sec=duration,
        )


# ------------------------------------------------------------------- factory


class SpeechToText:
    """Provider-agnostic entry point. Singleton within the process."""

    _instance: SpeechToText | None = None

    def __init__(self) -> None:
        provider = get_settings().stt_provider
        self.provider_name = provider
        self.backend: STTBackend = GroqSTT() if provider == "groq" else LocalWhisperSTT()

    @classmethod
    def instance(cls) -> SpeechToText:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Drop the cached instance — used by tests that switch providers."""
        cls._instance = None

    def transcribe_pcm(
        self, pcm: np.ndarray, sample_rate: int = 16000, language: str | None = None
    ) -> Transcription:
        return self.backend.transcribe_pcm(pcm, sample_rate=sample_rate, language=language)

    def transcribe_wav_bytes(self, data: bytes, language: str | None = None) -> Transcription:
        """Decode a WAV byte string, downmix/resample to 16kHz mono, transcribe."""
        with wave.open(io.BytesIO(data), "rb") as w:
            sr = w.getframerate()
            n_frames = w.getnframes()
            n_channels = w.getnchannels()
            sampwidth = w.getsampwidth()
            raw = w.readframes(n_frames)

        if sampwidth == 2:
            pcm = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        elif sampwidth == 4:
            pcm = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
        else:
            raise ValueError(f"Unsupported sample width: {sampwidth}")

        if n_channels > 1:
            pcm = pcm.reshape(-1, n_channels).mean(axis=1)

        if sr != 16000:
            new_len = int((len(pcm) / sr) * 16000)
            pcm = np.interp(
                np.linspace(0, len(pcm), new_len, endpoint=False),
                np.arange(len(pcm)),
                pcm,
            ).astype(np.float32)
            sr = 16000

        return self.transcribe_pcm(pcm, sample_rate=sr, language=language)
