"""Realtime voice pipeline: PCM-in (WebSocket) -> text -> LLM -> TTS audio-out.

For MVP, the flow is:
  client sends {type: "pcm", data: <bytes>} frames
  server buffers them, runs STT on commit, then LLM + TTS
  server streams {type: "transcript", ...} and {type: "audio", ...} back

The frontend handles capture (mic) and playback (audio element).
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np

from ..agent.runner import AgentRunner
from ..config import get_settings
from ..db import Call, async_session_scope
from ..logging import get_logger
from ..schemas import CallTurn


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

    # ---- Caller verification state ----
    # True only after a successful two-factor verify_caller. Write actions and
    # order details must not be disclosed until this flips.
    verified: bool = False
    verify_attempts: int = 0
    company_name: str = ""

    # ---- Structured outcome, filled by the log_call_outcome tool ----
    reason: str = ""
    solution: str = ""
    resolution_status: str = ""  # resolved | partial | unresolved
    satisfaction: str = ""  # happy | neutral | unhappy
    follow_up_required: bool = False
    related_order: str = ""
    sheet_synced: bool = False
    # In-flight background Google Sheets write, if any. Deliberately NOT awaited
    # during the call — see log_call_outcome. end_session() drains it once the
    # caller has hung up, when waiting costs nothing.
    sheet_task: Any = None

    def append_pcm(self, chunk: bytes) -> None:
        # ponytail: cap at 60s of 16kHz PCM (~1.9 MB) to prevent OOM
        MAX_BYTES = 1_920_000
        if len(self.pcm_buffer) >= MAX_BYTES:
            return
        self.pcm_buffer.extend(chunk[: MAX_BYTES - len(self.pcm_buffer)])

    def reset_pcm(self) -> None:
        self.pcm_buffer.clear()


class VoicePipeline:
    """Manages live call sessions over WebSocket."""

    def __init__(self) -> None:
        from .stt import SpeechToText
        from .tts import TextToSpeech

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
        call_id: str | None = None,
    ) -> CallSession:

        s = get_settings()
        call_id = call_id or f"call_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
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

    async def end_session(self, call_id: str, outcome: str = "resolved") -> CallSession | None:
        session = self._sessions.pop(call_id, None)
        if not session:
            return None
        session.ended_at = time.time()
        # Only overwrite the outcome if the agent didn't already log a real one.
        if not session.resolution_status:
            session.outcome = outcome
        await self._log_abandoned_if_needed(session)
        await self._drain_sheet_task(session)
        await self._persist(session)
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
        t0 = time.time()
        transcription = await loop.run_in_executor(
            None,
            lambda: self.stt.transcribe_pcm(pcm, sample_rate=session.pcm_sample_rate),
        )
        user_text = transcription.text.strip()
        log.info("timing.stt", ms=int((time.time() - t0) * 1000), confidence=transcription.confidence, lang=transcription.language)
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
        t0 = time.time()
        tts_result = await self.tts.synth(agent_text, lang_hint=session.language)
        log.info("timing.tts", ms=int((time.time() - t0) * 1000), text_len=len(agent_text))

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

    async def _drain_sheet_task(self, session: CallSession, timeout: float = 8.0) -> None:
        """Wait for the background Google Sheets write, now the call has ended.

        `log_call_outcome` deliberately does not await this — Google being slow
        must never be heard as dead air by a live caller. By the time we get
        here the caller has hung up, so waiting is free and lets us record
        `sheet_synced` accurately before persisting.

        A timeout is not an error: Postgres still holds the outcome with
        sheet_synced=0, which is both recoverable and visible on the dashboard.
        """
        task = session.sheet_task
        if task is None:
            return
        session.sheet_task = None
        try:
            result = await asyncio.wait_for(asyncio.shield(task), timeout=timeout)
            session.sheet_synced = bool(result.get("ok"))
            if not session.sheet_synced:
                log.warning(
                    "call.sheet_not_synced",
                    call_id=session.call_id,
                    reason=result.get("reason"),
                )
        except asyncio.TimeoutError:
            log.warning("call.sheet_timeout", call_id=session.call_id, timeout=timeout)
            session.sheet_synced = False
        except Exception as e:
            log.warning("call.sheet_failed", call_id=session.call_id, error=str(e))
            session.sheet_synced = False

    async def _log_abandoned_if_needed(self, session: CallSession) -> None:
        """Write a Sheets row for calls that ended without a logged outcome.

        A caller who hangs up mid-verification, or a call that drops, would
        otherwise leave no trace in the ops sheet — which is exactly the kind
        of failure the ops team most needs to see.
        """
        if session.resolution_status:
            return  # the agent already logged a real outcome

        from datetime import timedelta

        from ..integrations.gsheets import get_sheets_client

        turns = len(session.transcript)
        session.reason = session.reason or (
            "Caller hung up before stating a request" if turns <= 1 else "Call ended before resolution"
        )
        session.solution = session.solution or "No solution given — call ended early"
        session.resolution_status = "unresolved"
        session.satisfaction = session.satisfaction or "neutral"
        session.follow_up_required = True
        session.outcome = "abandoned"

        ist = timezone(timedelta(hours=5, minutes=30))
        try:
            result = await get_sheets_client().append_call_outcome(
                {
                    "timestamp": datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S"),
                    "call_id": session.call_id,
                    "caller_phone": session.caller_phone,
                    "caller_name": session.caller_name,
                    "company": session.company_name,
                    "verified": session.verified,
                    "language": session.language,
                    "reason": session.reason,
                    "solution": session.solution,
                    "resolution_status": session.resolution_status,
                    "satisfaction": session.satisfaction,
                    "follow_up_required": True,
                    "escalated": session.escalated,
                    "duration_sec": int((session.ended_at or time.time()) - session.started_at),
                    "related_order": session.related_order,
                }
            )
            session.sheet_synced = bool(result.get("ok"))
        except Exception as e:
            log.warning("call.abandoned_log_failed", call_id=session.call_id, error=str(e))

    async def _persist(self, session: CallSession) -> None:
        import json as _json

        t0 = time.time()
        try:
            async with async_session_scope() as db:
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
                    reason=session.reason,
                    solution=session.solution,
                    resolution_status=session.resolution_status,
                    satisfaction=session.satisfaction,
                    follow_up_required=1 if session.follow_up_required else 0,
                    sheet_synced=1 if session.sheet_synced else 0,
                    verified=1 if session.verified else 0,
                    transcript_json=_json.dumps(
                        [
                            {"role": t.role, "text": t.text, "at": t.at}
                            for t in session.transcript
                        ]
                    ),
                    actions_json=_json.dumps(session.actions),
                )
                await db.merge(row)
            log.info("timing.persist", call_id=session.call_id, ms=int((time.time() - t0) * 1000))
        except Exception as e:
            log.error("call.persist_failed", call_id=session.call_id, error=str(e))


def _b64(data: bytes) -> str:
    import base64

    return base64.b64encode(data).decode("ascii")
