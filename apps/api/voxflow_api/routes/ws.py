"""WebSocket endpoint for the browser phone simulator."""

from __future__ import annotations

import base64
import json
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..config import get_settings
from ..logging import get_logger
from ..services.pin_security import redact_pin_data, redact_pin_text
from ..voice.pipeline import CallSession, VoicePipeline


log = get_logger(__name__)
router = APIRouter()

# Single pipeline instance (in-memory). For multi-worker production, swap for Redis.
_pipeline: VoicePipeline | None = None


def get_pipeline() -> VoicePipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = VoicePipeline()
    return _pipeline


@router.websocket("/ws/call")
async def call_socket(ws: WebSocket) -> None:
    """Bidirectional voice stream.

    Client -> server message types:
      - {"type": "start", "caller_phone": "...", "caller_name": "...", "language": "hi|en"}
      - {"type": "pcm", "data": "<base64 int16 LE 16kHz mono>"}
      - {"type": "commit"}        # flush buffer -> STT -> LLM -> TTS
      - {"type": "text", "text": "..."}   # typed input fallback (testing)
      - {"type": "end"}

    Server -> client message types:
      - {"type": "ready", "call_id": "..."}
      - {"type": "transcript_partial", "text": "..."}    (incremental STT — v2)
      - {"type": "turn", ...}         (final turn with audio)
      - {"type": "info", "message": "..."}
      - {"type": "ended", "call_id": "..."}
    """
    await ws.accept()
    pipeline = get_pipeline()
    session: CallSession | None = None

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "message": "invalid_json"})
                continue

            t = msg.get("type")
            if t == "start":
                # Browser WebSockets cannot safely attach the application-owned
                # bearer identity used by REST. Until an authenticated WS
                # handshake is introduced, this surface is deliberately limited
                # to the fixed non-sensitive demonstration tenant. It cannot be
                # used to select or inspect a customer tenant by message data.
                requested_tenant = str(msg.get("tenant_id") or get_settings().demo_tenant_id)
                if requested_tenant != get_settings().demo_tenant_id:
                    await ws.send_json({"type": "error", "message": "simulator_tenant_authorization_required"})
                    continue
                session = pipeline.start_session(
                    caller_phone=msg.get("caller_phone", ""),
                    caller_name=msg.get("caller_name", ""),
                    language=msg.get("language"),
                    tenant_id=get_settings().demo_tenant_id,
                )
                await ws.send_json({"type": "ready", "call_id": session.call_id})

            elif t == "pcm":
                if session is None:
                    await ws.send_json({"type": "error", "message": "session_not_started"})
                    continue
                b64 = msg.get("data", "")
                try:
                    chunk = base64.b64decode(b64)
                except Exception:
                    await ws.send_json({"type": "error", "message": "bad_base64"})
                    continue
                session.append_pcm(chunk)

            elif t == "commit":
                if session is None:
                    await ws.send_json({"type": "error", "message": "session_not_started"})
                    continue
                # Day 54: stream first audio byte in ~150ms instead of buffering whole MP3.
                result = await pipeline.commit_audio_streaming(session, ws.send_json)
                await ws.send_json(redact_pin_data(result))

            elif t == "text":
                if session is None:
                    await ws.send_json({"type": "error", "message": "session_not_started"})
                    continue
                # Direct text path — also streams first byte via edge-tts chunks.
                from datetime import datetime, timezone

                user_text = (msg.get("text") or "").strip()
                if not user_text:
                    continue
                from ..schemas import CallTurn
                from ..agent.runner import AgentRunner

                session.transcript.append(CallTurn(role="caller", text=user_text, at=datetime.now(timezone.utc)))
                runner = AgentRunner()
                t_turn = time.perf_counter()
                agent_result = await runner.handle_turn(session=session, user_text=user_text)
                safe_user_text = redact_pin_text(user_text)
                safe_agent_text = redact_pin_text(agent_result.reply)
                safe_actions = redact_pin_data(agent_result.actions)
                session.transcript[-1].text = safe_user_text
                latency_ms = round((time.perf_counter() - t_turn) * 1000, 2)
                session.turn_latencies.append(latency_ms)
                session.transcript.append(CallTurn(role="agent", text=safe_agent_text, at=datetime.now(timezone.utc)))
                for a in safe_actions:
                    session.actions.append(a)
                    if a.get("name") == "escalate_to_human":
                        session.escalated = True
                await ws.send_json({"type": "turn_start", "agent_text": safe_agent_text, "user_text": safe_user_text})
                seq = 0
                try:
                    async for chunk in pipeline.tts.synth_stream(safe_agent_text, lang_hint=session.language):
                        await ws.send_json({"type": "audio_chunk", "seq": seq, "b64": base64.b64encode(chunk).decode("ascii"), "mime": "audio/mpeg"})
                        seq += 1
                except Exception as exc:
                    log.warning("tts.browser_fallback", error=redact_pin_text(str(exc)), text_len=len(safe_agent_text))
                await ws.send_json(redact_pin_data({
                    "type": "turn",
                    "user_text": safe_user_text,
                    "user_language": session.language,
                    "user_confidence": 1.0,
                    "agent_text": safe_agent_text,
                    "audio_fallback": seq == 0,
                    "actions": safe_actions,
                    "streamed_chunks": seq,
                }))

            elif t == "end":
                if session is not None:
                    await pipeline.end_session(session.call_id, outcome="resolved")
                    await ws.send_json({"type": "ended", "call_id": session.call_id})
                break

            else:
                await ws.send_json(
                    {"type": "error", "message": redact_pin_text(f"unknown_type:{t}")}
                )

    except WebSocketDisconnect:
        if session is not None:
            await pipeline.end_session(session.call_id, outcome="abandoned")
    except Exception as e:
        log.error("ws.error", error=redact_pin_text(str(e)))
        try:
            await ws.send_json({"type": "error", "message": "internal_error"})
        except Exception:
            pass
        if session is not None:
            await pipeline.end_session(session.call_id, outcome="error")
