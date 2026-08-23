"""Realtime voice pipeline: PCM-in (WebSocket) -> text -> LLM -> TTS audio-out.

For MVP, the flow is:
  client sends {type: "pcm", data: <bytes>} frames
  server buffers them, runs STT on commit, then LLM + TTS
  server streams {type: "transcript", ...} and {type: "audio", ...} back

The frontend handles capture (mic) and playback (audio element).
"""

from __future__ import annotations

import asyncio
import glob
import json
import os
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


def _json_default(value: Any) -> str:
    """Serialize timestamps and other non-JSON runtime values in session evidence."""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _sessions_dir() -> str:
    s = get_settings()
    d = os.path.join(s.resolved_data_dir, "sessions")
    os.makedirs(d, exist_ok=True)
    return d


def _snapshot_session(session: CallSession) -> None:
    try:
        sdir = _sessions_dir()
        fpath = os.path.join(sdir, f"{session.call_id}.json")
        data = {
            "call_id": session.call_id,
            "tenant_id": session.tenant_id,
            "language": session.language,
            "supplier_id": session.supplier_id,
            "caller_name": session.caller_name,
            "caller_phone": session.caller_phone,
            "intent": session.intent,
            "started_at": session.started_at,
            "ended_at": session.ended_at,
            "escalated": session.escalated,
            "outcome": session.outcome,
            "verified": session.verified,
            "company_name": session.company_name,
            "pin_verified": session.pin_verified,
            "reason": session.reason,
            "solution": session.solution,
            "resolution_status": session.resolution_status,
            "satisfaction": session.satisfaction,
            "follow_up_required": session.follow_up_required,
            "related_order": session.related_order,
            "recording_url": session.recording_url,
            "transcript": [{"role": t.role, "text": t.text, "at": t.at} for t in session.transcript],
            "actions": session.actions,
        }
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(data, f, default=_json_default)
    except Exception as e:
        log.warning("session.snapshot_failed", call_id=session.call_id, error=str(e))


def _remove_snapshot(call_id: str) -> None:
    try:
        fpath = os.path.join(_sessions_dir(), f"{call_id}.json")
        if os.path.exists(fpath):
            os.remove(fpath)
    except Exception as e:
        log.warning("session.snapshot_remove_failed", call_id=call_id, error=str(e))


@dataclass
class CallSession:
    call_id: str
    tenant_id: str = "varun"
    language: str = "en"
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
    verified: bool = False
    verify_attempts: int = 0
    company_name: str = ""
    # ---- Tier 2 PIN Verification state ----
    pin_verified: bool = False
    pin_attempts: int = 0
    known_caller: bool = False
    recording_url: str | None = None
    identified_by_phone: bool = False

    # ---- Structured outcome, filled by the log_call_outcome tool ----
    reason: str = ""
    solution: str = ""
    resolution_status: str = ""  # resolved | partial | unresolved
    satisfaction: str = ""  # happy | neutral | unhappy
    follow_up_required: bool = False
    related_order: str = ""
    sheet_synced: bool = False
    sheet_task: Any = None

    def append_pcm(self, chunk: bytes) -> None:
        MAX_BYTES = 1_920_000
        if len(self.pcm_buffer) >= MAX_BYTES:
            return
        self.pcm_buffer.extend(chunk[: MAX_BYTES - len(self.pcm_buffer)])

    def reset_pcm(self) -> None:
        self.pcm_buffer.clear()


class VoicePipeline:
    """Manages live call sessions over WebSocket with persistent recovery."""

    def __init__(self) -> None:
        from .stt import SpeechToText
        from .tts import TextToSpeech

        self.stt = SpeechToText.instance()
        self.tts = TextToSpeech()
        self.agent = AgentRunner()
        self._sessions: dict[str, CallSession] = {}
        self._silence_threshold_ms = 600

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
        _snapshot_session(session)
        log.info("call.started", call_id=call_id, tenant_id=session.tenant_id, language=lang, caller_phone=caller_phone)
        return session

    def get_session(self, call_id: str) -> CallSession | None:
        return self._sessions.get(call_id)

    async def end_session(self, call_id: str, outcome: str = "resolved") -> CallSession | None:
        session = self._sessions.pop(call_id, None)
        if not session:
            return None
        session.ended_at = time.time()
        if not session.resolution_status:
            session.outcome = outcome
        await self._log_abandoned_if_needed(session)
        await self._drain_sheet_task(session)
        await self._persist(session)
        _remove_snapshot(session.call_id)
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

        if transcription.language in ("hi", "en"):
            session.language = transcription.language

        session.transcript.append(CallTurn(role="caller", text=user_text, at=time.time()))

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

        # Snapshot updated state
        _snapshot_session(session)

        # TTS is an enhancement for the browser simulator, not a reason to lose
        # a completed agent turn. The client can safely use browser speech when
        # a hosted TTS response is unavailable.
        tts_result = None
        t0 = time.time()
        try:
            tts_result = await self.tts.synth(agent_text, lang_hint=session.language)
            log.info("timing.tts", ms=int((time.time() - t0) * 1000), text_len=len(agent_text))
        except Exception as exc:
            log.warning("tts.browser_fallback", error=str(exc), text_len=len(agent_text))

        return {
            "type": "turn",
            "user_text": user_text,
            "user_language": transcription.language,
            "user_confidence": transcription.confidence,
            "agent_text": agent_text,
            "agent_audio_b64": _b64(tts_result.audio_bytes) if tts_result else None,
            "agent_audio_mime": tts_result.mime if tts_result else None,
            "audio_fallback": tts_result is None,
            "actions": agent_result.actions,
        }

    # ---------- Persistence ----------

    async def _drain_sheet_task(self, session: CallSession, timeout: float = 8.0) -> None:
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
        if session.resolution_status:
            return

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
                    recording_url=session.recording_url,
                    transcript_json=json.dumps(
                        [
                            {"role": t.role, "text": t.text, "at": t.at}
                            for t in session.transcript
                        ],
                        default=_json_default,
                    ),
                    actions_json=json.dumps(session.actions, default=_json_default),
                )
                await db.merge(row)
            log.info("timing.persist", call_id=session.call_id, ms=int((time.time() - t0) * 1000))
        except Exception as e:
            log.error("call.persist_failed", call_id=session.call_id, error=str(e))

    async def recover_orphaned_sessions(self) -> int:
        """Scan session snapshots from disk and recover unpersisted sessions."""
        sdir = _sessions_dir()
        files = glob.glob(os.path.join(sdir, "*.json"))
        if not files:
            return 0

        recovered = 0
        for fpath in files:
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                call_id = data.get("call_id")
                if not call_id:
                    os.remove(fpath)
                    continue

                # Reconstruct session
                transcript = [
                    CallTurn(role=t.get("role", ""), text=t.get("text", ""), at=t.get("at", 0))
                    for t in data.get("transcript", [])
                ]
                session = CallSession(
                    call_id=call_id,
                    tenant_id=data.get("tenant_id", "varun"),
                    language=data.get("language", "en"),
                    supplier_id=data.get("supplier_id"),
                    caller_name=data.get("caller_name", ""),
                    caller_phone=data.get("caller_phone", ""),
                    intent=data.get("intent", ""),
                    transcript=transcript,
                    actions=data.get("actions", []),
                    started_at=data.get("started_at", time.time()),
                    ended_at=data.get("ended_at", time.time()),
                    escalated=data.get("escalated", False),
                    outcome=data.get("outcome", "interrupted"),
                    verified=data.get("verified", False),
                    company_name=data.get("company_name", ""),
                    pin_verified=data.get("pin_verified", False),
                    reason=data.get("reason", "Interrupted/Recovered session"),
                    solution=data.get("solution", ""),
                    resolution_status=data.get("resolution_status", "unresolved"),
                    satisfaction=data.get("satisfaction", "neutral"),
                    follow_up_required=data.get("follow_up_required", False),
                    related_order=data.get("related_order", ""),
                    recording_url=data.get("recording_url"),
                )
                await self._persist(session)
                _remove_snapshot(call_id)
                recovered += 1
                log.info("session.recovered_orphaned", call_id=call_id)
            except Exception as e:
                log.warning("session.recovery_failed", file=os.path.basename(fpath), error=str(e))

        return recovered


def _b64(data: bytes) -> str:
    import base64

    return base64.b64encode(data).decode("ascii")
