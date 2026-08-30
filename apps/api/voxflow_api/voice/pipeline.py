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
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np

from ..agent.runner import AgentRunner
from ..config import get_settings
from ..db import Call, async_session_scope
from ..logging import get_logger
from ..schemas import CallTurn
from ..services.escalation_service import compute_sla_due_at, derive_escalation_priority
from ..services.pin_security import redact_pin_data, redact_pin_text


log = get_logger(__name__)


def _json_default(value: Any) -> str:
    """Serialize timestamps and other non-JSON runtime values in session evidence."""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _redact_session_evidence(session: CallSession) -> None:
    """Redact caller-controlled text before snapshots, persistence, or mirrors.

    ``route_policy`` is deliberately NOT redacted: it stores the authorization
    bindings (supplier IDs) that ``verify_caller``/``verify_pin`` established.
    A blanket ``redact_pin_data`` pass rewrites numeric supplier IDs into
    ``[REDACTED PIN]`` and silently unbinds verification mid-call. The values
    are internal identifiers, never caller free-text speech.
    """
    for turn in session.transcript:
        turn.text = redact_pin_text(turn.text)
    session.actions = redact_pin_data(session.actions)
    for attr in ("caller_name", "company_name", "intent", "reason", "solution", "related_order"):
        value = getattr(session, attr, None)
        if isinstance(value, str):
            setattr(session, attr, redact_pin_text(value))


def _sessions_dir() -> str:
    s = get_settings()
    d = os.path.join(s.resolved_data_dir, "sessions")
    os.makedirs(d, exist_ok=True)
    return d


def _snapshot_session(session: CallSession) -> None:
    try:
        _redact_session_evidence(session)
        sdir = _sessions_dir()
        fpath = os.path.join(sdir, f"{session.call_id}.json")
        data = {
            "call_id": session.call_id,
            "tenant_id": session.tenant_id,
            "language": session.language,
            "supplier_id": session.supplier_id,
            "caller_name": redact_pin_text(session.caller_name),
            # caller_phone is structured telephony metadata (an E.164-style
            # number), never caller free-text speech. The 4-8 digit PIN
            # redaction regex would otherwise mangle every phone number's
            # digit groups into "[REDACTED PIN]" placeholders.
            "caller_phone": session.caller_phone,
            "intent": session.intent,
            "started_at": session.started_at,
            "ended_at": session.ended_at,
            "escalated": session.escalated,
            "outcome": session.outcome,
            "verified": session.verified,
            "company_name": session.company_name,
            "pin_verified": session.pin_verified,
            "route_policy": session.route_policy,
            "telephony_provider": session.telephony_provider,
            "inbound_did": session.inbound_did,
            "verification_mode": session.verification_mode,
            "route_language": session.route_language,
            "reason": session.reason,
            "solution": session.solution,
            "resolution_status": session.resolution_status,
            "satisfaction": session.satisfaction,
            "follow_up_required": session.follow_up_required,
            "related_order": session.related_order,
            "recording_url": session.recording_url,
            "transcript": [
                {"role": t.role, "text": redact_pin_text(t.text), "at": t.at}
                for t in session.transcript
            ],
            "actions": redact_pin_data(session.actions),
        }
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(data, f, default=_json_default)
    except Exception as e:
        log.warning(
            "session.snapshot_failed",
            call_id=redact_pin_text(session.call_id),
            error=redact_pin_text(str(e)),
        )


def _remove_snapshot(call_id: str) -> None:
    try:
        fpath = os.path.join(_sessions_dir(), f"{call_id}.json")
        if os.path.exists(fpath):
            os.remove(fpath)
    except Exception as e:
        log.warning(
            "session.snapshot_remove_failed",
            call_id=redact_pin_text(call_id),
            error=redact_pin_text(str(e)),
        )


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

    # ---- Inbound line route policy ----
    route_policy: dict[str, str] = field(default_factory=dict)
    telephony_provider: str = ""
    inbound_did: str = ""
    verification_mode: str = "standard"
    route_language: str = "tenant_default"

    # ---- Structured outcome, filled by the log_call_outcome tool ----
    reason: str = ""
    solution: str = ""
    resolution_status: str = ""  # resolved | partial | unresolved
    satisfaction: str = ""  # happy | neutral | unhappy
    follow_up_required: bool = False
    related_order: str = ""
    sheet_synced: bool = False
    sheet_task: Any = None
    # Day 42: per-turn server-side processing times (ms) recorded by callers of
    # handle_turn (e.g. the Amazon Connect route) for logging and latency SLOs.
    turn_latencies: list[float] = field(default_factory=list)
    # Day 43: consecutive silence/VAD timeout turns for progressive re-prompting
    silence_count: int = 0

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
        route_policy: dict[str, str] | None = None,
    ) -> CallSession:

        s = get_settings()
        call_id = call_id or f"call_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
        lang = language or s.tts_default_lang
        policy = dict(route_policy or {})
        session = CallSession(
            call_id=call_id,
            tenant_id=tenant_id or "varun",
            language=lang,
            caller_phone=caller_phone,
            caller_name=caller_name,
            route_policy=policy,
            telephony_provider=policy.get("provider", ""),
            inbound_did=policy.get("phone_number", ""),
            verification_mode=policy.get("verification_mode", "standard"),
            route_language=policy.get("route_language", "tenant_default"),
        )
        self._sessions[call_id] = session
        _snapshot_session(session)
        log.info(
            "call.started",
            call_id=redact_pin_text(call_id),
            tenant_id=redact_pin_text(session.tenant_id),
            language=redact_pin_text(lang),
            # caller_phone is structured telephony metadata, not free-text
            # caller speech; redacting it would corrupt real phone numbers.
            caller_phone=caller_phone,
        )
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
        # Day 42: mirror the finished call to Google Sheets off the request
        # path. The detached task must never delay the caller or the /end
        # response; Postgres above is already the durable source of truth.
        self._schedule_sheet_mirror(session)
        log.info(
            "call.ended",
            call_id=redact_pin_text(call_id),
            duration=int(session.ended_at - session.started_at),
            outcome=redact_pin_text(outcome),
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
        log.info(
            "timing.stt",
            ms=int((time.time() - t0) * 1000),
            confidence=transcription.confidence,
            lang=redact_pin_text(transcription.language),
        )
        if not user_text:
            return {"type": "info", "message": "empty_transcript"}

        if transcription.language in ("hi", "en"):
            session.language = transcription.language

        session.transcript.append(CallTurn(role="caller", text=user_text, at=time.time()))

        t_turn = time.perf_counter()
        agent_result = await self.agent.handle_turn(
            session=session,
            user_text=user_text,
        )
        safe_user_text = redact_pin_text(user_text)
        session.transcript[-1].text = safe_user_text
        latency_ms = round((time.perf_counter() - t_turn) * 1000, 2)
        session.turn_latencies.append(latency_ms)

        agent_text = redact_pin_text(agent_result.reply)
        safe_actions = redact_pin_data(agent_result.actions)
        session.transcript.append(CallTurn(role="agent", text=agent_text, at=time.time()))
        for a in safe_actions:
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
            log.warning(
                "tts.browser_fallback",
                error=redact_pin_text(str(exc)),
                text_len=len(agent_text),
            )

        return {
            "type": "turn",
            "user_text": safe_user_text,
            "user_language": transcription.language,
            "user_confidence": transcription.confidence,
            "agent_text": agent_text,
            "agent_audio_b64": _b64(tts_result.audio_bytes) if tts_result else None,
            "agent_audio_mime": tts_result.mime if tts_result else None,
            "audio_fallback": tts_result is None,
            "actions": safe_actions,
        }

    async def commit_audio_streaming(
        self, session: CallSession, send_json
    ) -> dict[str, Any]:
        """STT → LLM, then stream TTS chunks via `send_json` as they arrive.

        Keeps `commit_audio` intact for REST/tests. The WebSocket path calls
        this so the browser hears the first byte in ~150ms (TTFB) instead of
        waiting for the whole MP3 (~300ms).
        Protocol:
          -> {"type":"turn_start","agent_text":...}
          -> {"type":"audio_chunk","seq":0,"b64":...} * N
          -> {"type":"turn","agent_text":...,"audio_fallback":bool,"actions":...}
        """

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
        log.info("timing.stt", ms=int((time.time() - t0) * 1000), confidence=transcription.confidence, lang=redact_pin_text(transcription.language))
        if not user_text:
            return {"type": "info", "message": "empty_transcript"}

        if transcription.language in ("hi", "en"):
            session.language = transcription.language

        session.transcript.append(CallTurn(role="caller", text=user_text, at=time.time()))

        t_turn = time.perf_counter()
        agent_result = await self.agent.handle_turn(session=session, user_text=user_text)
        safe_user_text = redact_pin_text(user_text)
        session.transcript[-1].text = safe_user_text
        latency_ms = round((time.perf_counter() - t_turn) * 1000, 2)
        session.turn_latencies.append(latency_ms)

        agent_text = redact_pin_text(agent_result.reply)
        safe_actions = redact_pin_data(agent_result.actions)
        session.transcript.append(CallTurn(role="agent", text=agent_text, at=time.time()))
        for a in safe_actions:
            session.actions.append(a)
            if a.get("name") == "escalate_to_human":
                session.escalated = True
        _snapshot_session(session)

        # Tell the UI what the agent said immediately — text renders before audio.
        await send_json({"type": "turn_start", "agent_text": agent_text, "user_text": safe_user_text, "user_language": transcription.language})

        # Stream TTS chunks as they are synthesized.
        first_byte_ms: int | None = None
        t_tts = time.time()
        seq = 0
        total_bytes = 0
        try:
            async for chunk in self.tts.synth_stream(agent_text, lang_hint=session.language):
                if first_byte_ms is None:
                    first_byte_ms = int((time.time() - t_tts) * 1000)
                    log.info("timing.tts_first_byte", ms=first_byte_ms, text_len=len(agent_text))
                total_bytes += len(chunk)
                await send_json({"type": "audio_chunk", "seq": seq, "b64": _b64(chunk), "mime": "audio/mpeg"})
                seq += 1
            log.info("timing.tts_stream", ms=int((time.time() - t_tts) * 1000), chunks=seq, bytes=total_bytes, text_len=len(agent_text))
            audio_fallback = seq == 0
        except Exception as exc:
            log.warning("tts.browser_fallback", error=redact_pin_text(str(exc)), text_len=len(agent_text))
            audio_fallback = True
            seq = 0

        # Final turn (backward-compatible with the old single-blob shape — frontend
        # that ignores audio_chunk can still use agent_text).
        return {
            "type": "turn",
            "user_text": safe_user_text,
            "user_language": transcription.language,
            "user_confidence": transcription.confidence,
            "agent_text": agent_text,
            "agent_audio_b64": None,
            "agent_audio_mime": "audio/mpeg" if not audio_fallback else None,
            "audio_fallback": audio_fallback,
            "actions": safe_actions,
            "streamed_chunks": seq,
            "ttfb_ms": first_byte_ms,
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
                    call_id=redact_pin_text(session.call_id),
                    reason=redact_pin_data(result.get("reason")),
                )
        except asyncio.TimeoutError:
            log.warning(
                "call.sheet_timeout",
                call_id=redact_pin_text(session.call_id),
                timeout=timeout,
            )
            session.sheet_synced = False
        except Exception as e:
            log.warning(
                "call.sheet_failed",
                call_id=redact_pin_text(session.call_id),
                error=redact_pin_text(str(e)),
            )
            session.sheet_synced = False

    async def _log_abandoned_if_needed(self, session: CallSession) -> None:
        """Fill structured outcome fields for a call that ended without a
        log_call_outcome tool call. No network IO here — the Sheets mirror is
        owned by the detached end-of-call task."""
        if session.resolution_status:
            return

        turns = len(session.transcript)
        session.reason = session.reason or (
            "Caller hung up before stating a request" if turns <= 1 else "Call ended before resolution"
        )
        session.solution = session.solution or "No solution given — call ended early"
        session.resolution_status = "unresolved"
        session.satisfaction = session.satisfaction or "neutral"
        session.follow_up_required = True
        session.outcome = "abandoned"

    # ---------- Day 42 Google Sheets mirror (gated, non-blocking, idempotent) ----------

    _sheet_inflight: set[str] = set()
    _background_tasks: set["asyncio.Task[None]"] = set()

    def sheet_mirror_enabled(self, tenant_id: str) -> bool:
        """Day 42 gate: per-tenant allow-list AND a fully configured client.

        The durable side-effect engine stays parked; this is the single
        permitted activation and it covers only the call-logging row.
        """
        s = get_settings()
        if tenant_id not in s.sheets_call_log_tenant_ids:
            return False
        from ..integrations import gsheets

        return gsheets.get_sheets_client().is_configured()

    @staticmethod
    def sheet_row_for(session: CallSession) -> dict[str, Any]:
        """Build the canonical mirror-row payload (stable column mapping)."""
        ist = timezone(timedelta(hours=5, minutes=30))
        caller_turns = [t.text for t in session.transcript if t.role == "caller" and t.text]
        agent_turns = [t.text for t in session.transcript if t.role == "agent" and t.text]
        question = session.reason or (caller_turns[0] if caller_turns else "")
        answer = session.solution or (agent_turns[-1] if agent_turns else "")
        latencies = [ms for ms in session.turn_latencies if ms > 0]
        avg_latency = round(sum(latencies) / len(latencies)) if latencies else ""
        return {
            "timestamp": datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S"),
            "call_id": session.call_id,
            "caller_phone": session.caller_phone,
            "caller_name": redact_pin_text(session.caller_name),
            "company": redact_pin_text(session.company_name),
            "verified": session.verified,
            "language": session.language,
            "reason": redact_pin_text(session.reason),
            "solution": redact_pin_text(session.solution),
            "resolution_status": session.resolution_status,
            "satisfaction": session.satisfaction,
            "follow_up_required": session.follow_up_required,
            "escalated": session.escalated,
            "duration_sec": int((session.ended_at or time.time()) - session.started_at),
            "related_order": redact_pin_text(session.related_order),
            "tenant": session.tenant_id,
            "question": redact_pin_text(question),
            "answer": redact_pin_text(answer),
            "turn_latency_ms": avg_latency,
        }

    def _schedule_sheet_mirror(self, session: CallSession) -> None:
        """Schedule the detached mirror write. Never raises, never blocks."""
        try:
            if not self.sheet_mirror_enabled(session.tenant_id):
                return
            # In-process idempotency: one mirror per call_id even under races.
            if session.call_id in VoicePipeline._sheet_inflight:
                return
            VoicePipeline._sheet_inflight.add(session.call_id)
            task = asyncio.create_task(self._mirror_sheet(session))
            VoicePipeline._background_tasks.add(task)
            task.add_done_callback(VoicePipeline._background_tasks.discard)
        except Exception as e:
            log.warning(
                "call.sheet_schedule_failed",
                call_id=redact_pin_text(session.call_id),
                error=redact_pin_text(str(e)),
            )
            VoicePipeline._sheet_inflight.discard(session.call_id)

    async def _mirror_sheet(self, session: CallSession) -> None:
        """Write exactly one Sheet row for this call, guarded by Postgres."""
        from ..integrations import gsheets

        call_id = session.call_id
        try:
            from sqlalchemy import select

            async with async_session_scope() as db:
                row = (await db.execute(select(Call).where(Call.id == call_id))).scalars().first()
                if row is None:
                    log.warning(
                        "call.sheet_mirror_missing_db_row",
                        call_id=redact_pin_text(call_id),
                    )
                    return
                if row.sheet_synced:
                    return  # already mirrored (crash/retry safety)
                payload = self.sheet_row_for(session)

            result = await gsheets.get_sheets_client().append_call_outcome(payload, queue_on_failure=False)
            if result.get("ok"):
                await gsheets._mark_call_sheet_synced(call_id)
                session.sheet_synced = True
                log.info(
                    "call.sheet_synced",
                    call_id=redact_pin_text(call_id),
                    tab=redact_pin_data(result.get("tab")),
                )
            else:
                log.warning(
                    "call.sheet_not_synced",
                    call_id=redact_pin_text(call_id),
                    reason=redact_pin_data(result.get("reason")),
                )
        except Exception as e:
            log.error(
                "call.sheet_failed",
                call_id=redact_pin_text(call_id),
                error=redact_pin_text(str(e)),
            )
        finally:
            VoicePipeline._sheet_inflight.discard(call_id)

    async def drain_background_tasks(self, timeout: float = 10.0) -> None:
        """Await detached end-of-call tasks (tests + graceful shutdown)."""
        pending = [t for t in list(VoicePipeline._background_tasks) if not t.done()]
        if pending:
            await asyncio.wait(pending, timeout=timeout)

    async def _persist(self, session: CallSession) -> None:
        t0 = time.time()
        latencies = [ms for ms in session.turn_latencies if ms > 0]
        try:
            is_escalated = bool(session.escalated or session.follow_up_required)
            esc_priority = derive_escalation_priority(
                satisfaction=session.satisfaction,
                reason=session.reason,
                follow_up_required=bool(session.follow_up_required),
                verified=bool(session.verified),
            )
            started_dt = datetime.fromtimestamp(session.started_at, tz=timezone.utc)
            sla_due = compute_sla_due_at(priority=esc_priority, base_sla_minutes=60, from_time=started_dt) if is_escalated else None

            async with async_session_scope() as db:
                row = Call(
                    id=session.call_id,
                    tenant_id=session.tenant_id,
                    started_at=started_dt,
                    ended_at=datetime.fromtimestamp(session.ended_at or session.started_at, tz=timezone.utc),
                    duration_sec=int((session.ended_at or session.started_at) - session.started_at),
                    avg_turn_latency_ms=round(sum(latencies) / len(latencies)) if latencies else 0,
                    supplier_id=session.supplier_id,
                    # caller_phone is structured telephony metadata, not
                    # free-text caller speech; redacting it would corrupt the
                    # persisted phone number's digit groups.
                    caller_phone=session.caller_phone,
                    caller_name=redact_pin_text(session.caller_name),
                    language=session.language,
                    intent=session.intent,
                    outcome=session.outcome,
                    escalated=1 if session.escalated else 0,
                    reason=redact_pin_text(session.reason),
                    solution=redact_pin_text(session.solution),
                    resolution_status=session.resolution_status,
                    satisfaction=session.satisfaction,
                    follow_up_required=1 if session.follow_up_required else 0,
                    escalation_priority=esc_priority if is_escalated else "medium",
                    escalation_status="pending" if is_escalated else "none",
                    sla_due_at=sla_due,
                    sheet_synced=1 if session.sheet_synced else 0,
                    verified=1 if session.verified else 0,
                    recording_url=session.recording_url,
                    transcript_json=json.dumps(
                        [
                            {"role": t.role, "text": redact_pin_text(t.text), "at": t.at}
                            for t in session.transcript
                        ],
                        default=_json_default,
                    ),
                    actions_json=json.dumps(redact_pin_data(session.actions), default=_json_default),
                )
                await db.merge(row)
            log.info(
                "timing.persist",
                call_id=redact_pin_text(session.call_id),
                ms=int((time.time() - t0) * 1000),
            )
        except Exception as e:
            log.error(
                "call.persist_failed",
                call_id=redact_pin_text(session.call_id),
                error=redact_pin_text(str(e)),
            )

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
                    route_policy=data.get("route_policy", {}),
                    telephony_provider=data.get("telephony_provider", ""),
                    inbound_did=data.get("inbound_did", ""),
                    verification_mode=data.get("verification_mode", "standard"),
                    route_language=data.get("route_language", "tenant_default"),
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
                log.info(
                    "session.recovered_orphaned",
                    call_id=redact_pin_text(call_id),
                )
            except Exception as e:
                log.warning(
                    "session.recovery_failed",
                    file=redact_pin_text(os.path.basename(fpath)),
                    error=redact_pin_text(str(e)),
                )

        return recovered


def _b64(data: bytes) -> str:
    import base64

    return base64.b64encode(data).decode("ascii")
