"""Realtime voice pipeline: PCM-in (WebSocket) -> text -> LLM -> TTS audio-out.

For MVP, the flow is:
  client sends {type: "pcm", data: <bytes>} frames
  server buffers them, runs STT on commit, then LLM + TTS
  server streams {type: "transcript", ...} and {type: "audio", ...} back

The frontend handles capture (mic) and playback (audio element).
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import numpy as np

from ..agent.runner import AgentRunner
from ..config import get_settings
from ..db import Call, session_scope
from ..logging import get_logger
from ..schemas import CallTurn
from .stt import SpeechToText
from .tts import TextToSpeech


log = get_logger(__name__)


@dataclass
class CallSession:
    call_id: str
    tenant_id: str = "varun"
    language: str = "hi"
    supplier_id: str | None = None
    caller_name: str = ""
    caller_phone: str = ""
    intent: str = ""
    transcript: list[CallTurn] = field(default_factory=list)
    actions: list[dict[str, Any]] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    ended_at: float | None = None
    escalated: bool = False
    outcome: str = "in_progress"
    pcm_buffer: bytearray = field(default_factory=bytearray)
    pcm_sample_rate: int = 16000

    def append_pcm(self, chunk: bytes) -> None:
        self.pcm_buffer.extend(chunk)

    def reset_pcm(self) -> None:
        self.pcm_buffer.clear()


class VoicePipeline:
    """Manages live call sessions over WebSocket."""

    def __init__(self) -> None:
        self.stt = SpeechToText.instance()
        self.tts = TextToSpeech()
        self.agent = AgentRunner()
        self._sessions: dict[str, CallSession] = {}
        self._silence_threshold_ms = 600  # commit after 600ms of silence

    # ---------- Session lifecycle ----------

    def start_session(
        self,
        caller_phone: str = "",
        caller_name: str = "",
        language: str | None = None,
        tenant_id: str | None = None,
    ) -> CallSession:
        from ..config import get_settings

        s = get_settings()
        call_id = f"call_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
        lang = language or s.tts_default_lang
        session = CallSession(
            call_id=call_id,
            tenant_id=tenant_id or "varun",
            language=lang,
            caller_phone=caller_phone,
            caller_name=caller_name,
        )
        self._sessions[call_id] = session
        log.info("call.started", call_id=call_id, tenant_id=session.tenant_id, language=lang, caller_phone=caller_phone)
        return session

    def get_session(self, call_id: str) -> CallSession | None:
        return self._sessions.get(call_id)

    def end_session(self, call_id: str, outcome: str = "resolved") -> CallSession | None:
        session = self._sessions.pop(call_id, None)
        if not session:
            return None
        session.ended_at = time.time()
        session.outcome = outcome
        self._persist(session)
        log.info(
            "call.ended",
            call_id=call_id,
            duration=int(session.ended_at - session.started_at),
            outcome=outcome,
            escalated=session.escalated,
            turns=len(session.transcript),
        )
        return session

    # ---------- Audio processing ----------

    async def commit_audio(self, session: CallSession) -> dict[str, Any]:
        """Transcribe buffered PCM, run agent, return TTS audio bytes."""
        if not session.pcm_buffer:
            return {"type": "info", "message": "no_audio"}

        pcm = np.frombuffer(bytes(session.pcm_buffer), dtype=np.int16).astype(np.float32) / 32768.0
        session.reset_pcm()

        loop = asyncio.get_running_loop()
        transcription = await loop.run_in_executor(
            None,
            lambda: self.stt.transcribe_pcm(pcm, sample_rate=session.pcm_sample_rate),
        )
        user_text = transcription.text.strip()
        if not user_text:
            return {"type": "info", "message": "empty_transcript"}

        # Update session language hint from STT detection
        if transcription.language in ("hi", "en"):
            session.language = transcription.language

        # Log caller turn
        session.transcript.append(CallTurn(role="caller", text=user_text, at=time.time()))

        # Run the agent (LLM + tools)
        agent_result = await self.agent.handle_turn(
            session=session,
            user_text=user_text,
        )

        agent_text = agent_result.reply
        session.transcript.append(CallTurn(role="agent", text=agent_text, at=time.time()))
        for a in agent_result.actions:
            session.actions.append(a)
            if a.get("name") == "escalate_to_human":
                session.escalated = True

        # TTS
        tts_result = await self.tts.synth(agent_text, lang_hint=session.language)

        return {
            "type": "turn",
            "user_text": user_text,
            "user_language": transcription.language,
            "user_confidence": transcription.confidence,
            "agent_text": agent_text,
            "agent_audio_b64": _b64(tts_result.audio_bytes),
            "agent_audio_mime": tts_result.mime,
            "actions": agent_result.actions,
        }

    # ---------- Persistence ----------

    def _persist(self, session: CallSession) -> None:
        import json as _json
        from datetime import datetime, timezone

        try:
            with session_scope() as db:
                row = Call(
                    id=session.call_id,
                    tenant_id=session.tenant_id,
                    started_at=datetime.fromtimestamp(session.started_at, tz=timezone.utc),
                    ended_at=datetime.fromtimestamp(session.ended_at or session.started_at, tz=timezone.utc),
                    duration_sec=int((session.ended_at or session.started_at) - session.started_at),
                    supplier_id=session.supplier_id,
                    caller_phone=session.caller_phone,
                    caller_name=session.caller_name,
                    language=session.language,
                    intent=session.intent,
                    outcome=session.outcome,
                    escalated=1 if session.escalated else 0,
                    transcript_json=_json.dumps(
                        [
                            {"role": t.role, "text": t.text, "at": t.at}
                            for t in session.transcript
                        ]
                    ),
                    actions_json=_json.dumps(session.actions),
                )
                db.merge(row)
        except Exception as e:
            log.error("call.persist_failed", call_id=session.call_id, error=str(e))


def _b64(data: bytes) -> str:
    import base64

    return base64.b64encode(data).decode("ascii")
