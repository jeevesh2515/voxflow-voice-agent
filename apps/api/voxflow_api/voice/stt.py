"""Speech-to-text using faster-whisper (local, CPU-friendly)."""

from __future__ import annotations

import io
import wave
from dataclasses import dataclass

import numpy as np
from faster_whisper import WhisperModel

from ..config import get_settings
from ..logging import get_logger


log = get_logger(__name__)


@dataclass
class Transcription:
    text: str
    language: str
    confidence: float
    duration_sec: float


class SpeechToText:
    """Lazy-loaded Whisper model. Singleton within the process."""

    _instance: "SpeechToText | None" = None

    def __init__(self) -> None:
        s = get_settings()
        device = "auto"
        if s.whisper_device != "auto":
            device = s.whisper_device
        log.info(
            "stt.loading",
            model=s.whisper_model_size,
            device=device,
            compute_type=s.whisper_compute_type,
        )
        self.model = WhisperModel(
            s.whisper_model_size,
            device=device,
            compute_type=s.whisper_compute_type,
        )
        log.info("stt.ready", model=s.whisper_model_size)

    @classmethod
    def instance(cls) -> "SpeechToText":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def transcribe_pcm(
        self,
        pcm: np.ndarray,
        sample_rate: int = 16000,
        language: str | None = None,
    ) -> Transcription:
        """Transcribe a 1-D float32 numpy PCM array (mono, 16 kHz)."""
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

        text = " ".join(t for t in text_parts if t).strip()
        conf = float(np.mean(probs)) if probs else 0.0
        return Transcription(
            text=text,
            language=info.language or (language or "hi"),
            confidence=conf,
            duration_sec=duration,
        )

    def transcribe_wav_bytes(self, data: bytes, language: str | None = None) -> Transcription:
        """Decode a WAV byte string and transcribe."""
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
            # Cheap resample using linear interpolation. For high quality use librosa.
            duration = len(pcm) / sr
            new_len = int(duration * 16000)
            pcm = np.interp(
                np.linspace(0, len(pcm), new_len, endpoint=False),
                np.arange(len(pcm)),
                pcm,
            ).astype(np.float32)
            sr = 16000

        return self.transcribe_pcm(pcm, sample_rate=sr, language=language)
