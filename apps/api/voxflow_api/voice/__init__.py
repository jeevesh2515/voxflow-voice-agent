"""Voice pipeline: STT + TTS + WebSocket audio bridge."""

# Lazy imports — these modules have heavy deps (faster-whisper) and may not
# be installed in all environments (e.g. CI tests). Import directly from
# voice.stt, voice.tts, voice.pipeline when needed.

__all__ = []
