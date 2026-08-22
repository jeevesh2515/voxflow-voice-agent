"""Telnyx Voice + Media Streams routes.

Supports:
- TeXML inbound voice webhook (POST /telnyx/voice)
- Bidirectional WebSocket streaming (WS /telnyx/media)
- Call status / hangup callbacks (POST /telnyx/status)
- End-of-utterance VAD, Groq/faster-whisper STT, AgentRunner, Edge-TTS, and barge-in.
"""

from __future__ import annotations

import asyncio
import contextlib
import base64
import json
import re
import time
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

from ..config import get_settings
from ..db import Call, async_session_scope
from ..logging import get_logger
from ..telephony.registry import get_telephony_provider
from ..voice.pipeline import CallSession
from .twilio import (
    _SILENCE_MS,
    _SILENCE_RMS,
    _rms,
    mp3_to_pcm8k,
    mulaw_to_pcm,
    pcm_to_mulaw,
    resample_8k_to_16k,
)
from .ws import get_pipeline

log = get_logger(__name__)
router = APIRouter(prefix="/telnyx", tags=["telnyx"])

# CallSid -> caller metadata captured on POST /voice
_call_meta: dict[str, dict[str, str]] = {}

# Sliding-window rate limiting
_RATE_LIMIT_MAX = 30
_RATE_LIMIT_WINDOW = 60.0
_rate_buckets: dict[str, list[float]] = {}

_WS_RATE_LIMIT_MAX = 10
_ws_rate_buckets: dict[str, list[float]] = {}


def _rate_limited(client_ip: str) -> bool:
    now = time.monotonic()
    hits = _rate_buckets.setdefault(client_ip, [])
    cutoff = now - _RATE_LIMIT_WINDOW
    hits[:] = [t for t in hits if t > cutoff]
    if len(hits) >= _RATE_LIMIT_MAX:
        return True
    hits.append(now)
    if len(_rate_buckets) > 5000:
        for ip in [k for k, v in _rate_buckets.items() if not v]:
            _rate_buckets.pop(ip, None)
    return False


def _ws_rate_limited(client_ip: str) -> bool:
    now = time.monotonic()
    hits = _ws_rate_buckets.setdefault(client_ip, [])
    cutoff = now - _RATE_LIMIT_WINDOW
    hits[:] = [t for t in hits if t > cutoff]
    if len(hits) >= _WS_RATE_LIMIT_MAX:
        return True
    hits.append(now)
    if len(_ws_rate_buckets) > 5000:
        for ip in [k for k, v in _ws_rate_buckets.items() if not v]:
            _ws_rate_buckets.pop(ip, None)
    return False


async def _resolve_tenant(to_number: str) -> str:
    s = get_settings()
    if not to_number:
        return s.default_tenant_id

    from sqlalchemy import select
    from ..db import TenantPhoneNumber

    try:
        async with async_session_scope() as db:
            row = (
                await db.execute(
                    select(TenantPhoneNumber).where(
                        TenantPhoneNumber.phone_number == to_number,
                        TenantPhoneNumber.active == 1,
                    )
                )
            ).scalars().first()
            if row:
                return row.tenant_id
    except Exception as e:
        log.error("telnyx.tenant_lookup_failed", to=to_number, error=str(e))

    return s.default_tenant_id


@router.post("/voice")
async def telnyx_voice_webhook(request: Request) -> Response:
    """Return TeXML connecting audio streaming back to this server."""
    client_ip = request.client.host if request.client else "unknown"
    if _rate_limited(client_ip):
        log.warning("telnyx.rate_limited", ip=client_ip)
        raise HTTPException(status_code=429, detail="rate_limited")

    host = request.headers.get("host", "localhost:8000")
    if not re.match(r"^[\w\.\-]+(:\d+)?$", host):
        raise HTTPException(status_code=400, detail="invalid_host")

    form_dict: dict[str, Any] = {}
    # Attempt form parsing or JSON body parsing
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            form_dict = await request.json()
        except Exception:
            pass
    else:
        try:
            form = await request.form()
            form_dict = {k: str(v) for k, v in form.items()}
        except Exception:
            pass

    provider = get_telephony_provider("telnyx")
    if not provider.validate_webhook(request, form_dict, "/telnyx/voice"):
        log.warning("telnyx.invalid_signature", ip=client_ip)
        raise HTTPException(status_code=403, detail="invalid_signature")

    incoming = provider.parse_incoming_call(form_dict)
    tenant_id = await _resolve_tenant(incoming.to_number)

    if incoming.call_sid:
        _call_meta[incoming.call_sid] = {
            "caller_phone": incoming.caller_phone,
            "to_number": incoming.to_number,
            "tenant_id": tenant_id,
        }
    if len(_call_meta) > 1000:
        _call_meta.clear()

    log.info(
        "telnyx.voice_webhook",
        call_sid=incoming.call_sid,
        from_=incoming.caller_phone,
        to=incoming.to_number,
        tenant_id=tenant_id,
    )

    base = (get_settings().public_base_url or "").rstrip("/")
    ws_host = base.split("://", 1)[-1] if base else host
    texml = provider.generate_connect_response(ws_host, "/telnyx/media")

    return Response(
        content=texml,
        media_type="application/xml",
        headers={
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Cache-Control": "no-store, no-cache",
        },
    )


@router.post("/status")
async def telnyx_status_callback(request: Request) -> Response:
    """Handle Telnyx call status and completion callbacks."""
    try:
        data: dict[str, Any] = {}
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            data = await request.json()
        else:
            form = await request.form()
            data = {k: str(v) for k, v in form.items()}

        provider = get_telephony_provider("telnyx")
        incoming = provider.parse_incoming_call(data)
        log.info("telnyx.status_callback", call_sid=incoming.call_sid, provider=incoming.provider)
    except Exception as e:
        log.warning("telnyx.status_callback_error", error=str(e))

    return Response(content="<Response/>", media_type="application/xml")


# ---------- WebSocket Media Streaming ----------


@dataclass
class _TelnyxStreamState:
    stream_sid: str
    call_sid: str
    caller_phone: str = ""
    session: CallSession | None = None
    speech: bool = False
    last_speech_at: float = 0.0
    processing: bool = False
    task: asyncio.Task | None = None
    send_task: asyncio.Task | None = None
    last_turn: dict[str, Any] | None = None
    total_frames: int = 0
    total_bytes: int = 0


async def _send_telnyx_agent_audio(
    ws: WebSocket, st: _TelnyxStreamState, agent_audio_b64: str,
) -> None:
    """Encode agent TTS audio to mulaw and stream frames to Telnyx."""
    provider = get_telephony_provider("telnyx")
    try:
        mp3_bytes = base64.b64decode(agent_audio_b64)
        pcm_8k = mp3_to_pcm8k(mp3_bytes)
        mulaw_bytes = pcm_to_mulaw(pcm_8k)

        frame_size = 160
        total_bytes = len(mulaw_bytes)
        offset = 0

        log.info(
            "telnyx.media.send_audio_start",
            call_sid=st.call_sid,
            stream_sid=st.stream_sid,
            pcm_len=len(pcm_8k),
            mulaw_len=total_bytes,
        )

        burst_frames = 3
        while offset < total_bytes:
            chunk = mulaw_bytes[offset : offset + frame_size]
            offset += len(chunk)
            msg_text = provider.encode_audio_frame(chunk, st.stream_sid)
            await ws.send_text(msg_text)

            if burst_frames > 0:
                burst_frames -= 1
            else:
                await asyncio.sleep(0.02)

        log.info("telnyx.media.send_audio_complete", call_sid=st.call_sid)
    except asyncio.CancelledError:
        log.info("telnyx.media.send_audio_cancelled", call_sid=st.call_sid)
        with contextlib.suppress(Exception, asyncio.CancelledError):
            clear_text = provider.encode_clear(st.stream_sid)
            await ws.send_text(clear_text)
        raise
    except Exception as e:
        log.error("telnyx.media.send_audio_error", call_sid=st.call_sid, error=str(e))


async def _process_telnyx_utterance(st: _TelnyxStreamState, ws: WebSocket) -> None:
    session = st.session
    if session is None:
        return
    try:
        result = await get_pipeline().commit_audio(session)
        if result.get("type") == "turn":
            log.info(
                "telnyx.media.transcript",
                call_sid=st.call_sid,
                user_text=result["user_text"],
                agent_text=result["agent_text"],
                user_language=result.get("user_language"),
                user_confidence=result.get("user_confidence"),
            )
            st.last_turn = result
            agent_audio_b64 = result.get("agent_audio_b64")
            if agent_audio_b64:
                if st.send_task and not st.send_task.done():
                    st.send_task.cancel()
                st.send_task = asyncio.create_task(
                    _send_telnyx_agent_audio(ws, st, agent_audio_b64)
                )
    except Exception as e:
        log.error("telnyx.media.processing_error", call_sid=st.call_sid, error=str(e))
    finally:
        st.processing = False


async def _finalize_telnyx_stream(st: _TelnyxStreamState | None) -> None:
    if st is None:
        return

    try:
        if st.task:
            with contextlib.suppress(Exception, asyncio.CancelledError):
                await st.task

        if st.send_task and not st.send_task.done():
            st.send_task.cancel()
            with contextlib.suppress(Exception, asyncio.CancelledError):
                await st.send_task

        session = st.session
        if session is not None and session.pcm_buffer:
            try:
                result = await get_pipeline().commit_audio(session)
                if result.get("type") == "turn":
                    log.info(
                        "telnyx.media.transcript_flush",
                        call_sid=st.call_sid,
                        user_text=result["user_text"],
                    )
            except Exception as e:
                log.error("telnyx.media.final_flush_error", call_sid=st.call_sid, error=str(e))
    finally:
        try:
            await get_pipeline().end_session(st.call_sid, outcome="resolved")
        except Exception as e:
            log.error("telnyx.media.end_session_failed", call_sid=st.call_sid, error=str(e))


@router.websocket("/media")
async def telnyx_media_stream(ws: WebSocket) -> None:
    """WebSocket handler for Telnyx Media Streams audio."""
    client_ip = ws.client.host if ws.client else "unknown"
    if _ws_rate_limited(client_ip):
        log.warning("telnyx.media.ws_rate_limited", ip=client_ip)
        await ws.accept()
        await ws.close(code=1008, reason="rate_limited")
        return

    await ws.accept()
    st: _TelnyxStreamState | None = None
    provider = get_telephony_provider("telnyx")

    log.info("telnyx.media.connected")

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            event = msg.get("event")

            if event == "connected":
                log.info("telnyx.media.connected_event")

            elif event == "start":
                start_meta = provider.parse_media_start(msg)
                if not start_meta.call_sid:
                    continue
                meta = _call_meta.pop(start_meta.call_sid, {})
                session = get_pipeline().start_session(
                    caller_phone=meta.get("caller_phone", ""),
                    tenant_id=meta.get("tenant_id"),
                    call_id=start_meta.call_sid,
                )
                st = _TelnyxStreamState(
                    stream_sid=start_meta.stream_sid,
                    call_sid=start_meta.call_sid,
                    caller_phone=meta.get("caller_phone", ""),
                    session=session,
                )
                log.info(
                    "telnyx.media.start",
                    stream_sid=start_meta.stream_sid,
                    call_sid=start_meta.call_sid,
                    tenant_id=session.tenant_id,
                )

            elif event == "media":
                if st is None or st.session is None:
                    continue
                mulaw = provider.decode_audio_frame(msg)
                if not mulaw:
                    continue
                pcm_8k = mulaw_to_pcm(mulaw)
                now = time.monotonic()

                rms = _rms(pcm_8k)
                if rms > _SILENCE_RMS:
                    st.speech = True
                    st.last_speech_at = now
                    if st.send_task and not st.send_task.done():
                        st.send_task.cancel()

                st.session.append_pcm(resample_8k_to_16k(pcm_8k))
                st.total_frames += 1
                st.total_bytes += len(mulaw)

                if st.total_frames % 100 == 0:
                    log.info(
                        "telnyx.media.frame",
                        stream_sid=st.stream_sid,
                        frame_count=st.total_frames,
                        total_bytes=st.total_bytes,
                        mulaw_len=len(mulaw),
                        rms=round(rms, 1),
                    )

                if (
                    st.speech
                    and not st.processing
                    and (now - st.last_speech_at) * 1000 >= _SILENCE_MS
                ):
                    st.processing = True
                    st.task = asyncio.create_task(_process_telnyx_utterance(st, ws))

            elif event == "stop":
                break

            elif event == "mark":
                pass

            else:
                log.debug("telnyx.media.unknown_event", event=event)

    except WebSocketDisconnect:
        log.info("telnyx.media.disconnected", frames=st.total_frames if st else 0)
    except Exception as e:
        log.error("telnyx.media.error", error=str(e))
    finally:
        await _finalize_telnyx_stream(st)
