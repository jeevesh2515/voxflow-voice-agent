"""Twilio Voice + Media Streams routes (Day 7-9).

Day 7: TwiML webhook + Media Streams WebSocket, mulaw->PCM decode, 8k->16k resample.
Day 8: buffers decoded PCM per call, detects utterance boundaries via a simple
amplitude VAD, and feeds completed utterances into STT -> agent -> TTS pipeline.
Day 9: decodes agent TTS audio (MP3 -> PCM 8k), encodes to G.711 μ-law, and streams
paced 20ms frames back over the Media Streams WebSocket so the caller hears the reply.
Supports barge-in (cancellation on speech).
"""

from __future__ import annotations

import asyncio
import contextlib
import base64
import io
import json
import re
import time
from dataclasses import dataclass
from typing import Any

import av
import numpy as np
from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

from ..config import get_settings
from ..db import Call, async_session_scope
from ..logging import get_logger
from ..voice.pipeline import CallSession
from .ws import get_pipeline


log = get_logger(__name__)
router = APIRouter(prefix="/twilio", tags=["twilio"])

# VAD: an audio frame whose RMS is below this (int16 units) counts as silence.
# Real phone noise typically sits well under this; speech is usually > 3000.
# Tune after real multi-caller testing (Day 10).
_SILENCE_RMS = 800
# Trailing silence (ms) that marks the end of an utterance.
_SILENCE_MS = 450

# CallSid -> caller metadata captured on the POST /voice webhook; the WebSocket
# `start` event consumes it (Twilio's start event carries no From/To).
_call_meta: dict[str, dict[str, str]] = {}

# Sliding-window rate limit for the public webhook, keyed by client IP.
_RATE_LIMIT_MAX = 30       # requests...
_RATE_LIMIT_WINDOW = 60.0  # ...per this many seconds
_rate_buckets: dict[str, list[float]] = {}

# Separate rate limit for WebSocket /twilio/media connections.
# Twilio opens one WS per call, so 10/min per IP is generous for normal use.
_WS_RATE_LIMIT_MAX = 10
_ws_rate_buckets: dict[str, list[float]] = {}


def _rate_limited(client_ip: str) -> bool:
    """True if this IP has exceeded the webhook rate limit.

    /twilio/voice is a public unauthenticated POST endpoint. Without a cap,
    anyone who finds the URL can spin the agent up in a loop and burn the
    Groq/Twilio quota.
    """
    now = time.monotonic()
    hits = _rate_buckets.setdefault(client_ip, [])
    cutoff = now - _RATE_LIMIT_WINDOW
    hits[:] = [t for t in hits if t > cutoff]
    if len(hits) >= _RATE_LIMIT_MAX:
        return True
    hits.append(now)
    if len(_rate_buckets) > 5000:  # crude cap so the dict can't grow unbounded
        for ip in [k for k, v in _rate_buckets.items() if not v]:
            _rate_buckets.pop(ip, None)
    return False


def _ws_rate_limited(client_ip: str) -> bool:
    """True if this IP has exceeded the WebSocket connection rate limit.

    /twilio/media is a WebSocket endpoint. Twilio opens exactly one connection
    per call, so 10 connections per minute per IP is generous for legitimate use
    and still blocks runaway loops if the public URL is discovered.
    """
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


def _public_url(request: Request, path: str) -> str:
    """The absolute https URL Twilio used to reach us.

    Behind Caddy/nginx the app sees plain http on an internal port, so the URL
    Starlette reports is not the one Twilio signed. Signature validation fails
    unless we reconstruct it from the configured public base URL.
    """
    base = (get_settings().public_base_url or "").rstrip("/")
    if base:
        return f"{base}{path}"
    host = request.headers.get("host", "localhost:8000")
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    return f"{proto}://{host}{path}"


def _validate_twilio_signature(request: Request, form: dict[str, Any], path: str) -> bool:
    """Verify the X-Twilio-Signature header. Returns True when the request is trusted."""
    s = get_settings()
    if not s.twilio_validate_signature:
        return True
    if not s.twilio_auth_token:
        log.warning("twilio.signature_skipped", reason="no_auth_token_configured")
        return False

    signature = request.headers.get("X-Twilio-Signature", "")
    if not signature:
        return False

    try:
        from twilio.request_validator import RequestValidator
    except ImportError:
        log.error("twilio.sdk_missing", hint="pip install twilio")
        return False

    validator = RequestValidator(s.twilio_auth_token)
    return bool(validator.validate(_public_url(request, path), form, signature))


async def _resolve_tenant(to_number: str) -> str:
    """Map the dialed number to its tenant.

    Multi-tenancy is only real if the tenant comes from the number the caller
    dialed. Falling back to a default tenant for an unmapped number would serve
    one company's order data to another company's caller, so an unmapped number
    is logged loudly.
    """
    s = get_settings()
    if not to_number:
        return s.default_tenant_id

    from sqlalchemy import select

    from ..db import TenantPhoneNumber, async_session_scope

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
        log.error("twilio.tenant_lookup_failed", to=to_number, error=str(e))

    log.warning(
        "twilio.unmapped_number",
        to=to_number,
        fallback=s.default_tenant_id,
        hint="Add this number to tenant_phone_numbers to route it correctly.",
    )
    return s.default_tenant_id


# ---------- mulaw / PCM utilities ----------


def _ulaw2linear(ulaw_byte: int) -> int:
    """Expand one 8-bit μ-law byte to 16-bit signed linear PCM (G.711).

    Twilio Media Streams sends standard G.711 μ-law (RFC 3551): the transmitted
    codeword is bit-inverted, then segmented into sign / exponent / mantissa.
    """
    ulaw_byte = ~ulaw_byte & 0xFF
    sign = ulaw_byte & 0x80
    exponent = (ulaw_byte >> 4) & 0x07
    mantissa = ulaw_byte & 0x0F
    magnitude = ((2 * mantissa + 33) << exponent) - 33
    sample = magnitude << 2  # 13-bit companded range -> 16-bit
    return -sample if sign else sample


def linear_to_ulaw(sample: int) -> int:
    """Compress a 16-bit signed linear PCM sample to 8-bit μ-law byte (G.711).

    Inverse of _ulaw2linear. Clamps sample to int16 range, computes sign,
    exponent, and mantissa, then returns the bit-inverted byte.
    """
    sample = max(-32768, min(32767, sample))
    sign = 0x80 if sample < 0 else 0x00
    mag = -sample if sample < 0 else sample
    mag_biased = (mag >> 2) + 33
    mag_biased = min(mag_biased, 8159)

    exponent = 0
    for exp in range(7, -1, -1):
        if mag_biased & (1 << (exp + 5)):
            exponent = exp
            break

    mantissa = (mag_biased >> (exponent + 1)) & 0x0F
    return ~(sign | (exponent << 4) | mantissa) & 0xFF


# ---------- Vectorised codec lookup tables ----------
#
# The scalar functions above are the reference implementation. These tables are
# generated FROM them at import, so the fast paths below are correct by
# construction — there is no second implementation to drift out of sync.
#
# Why this matters: Twilio sends 50 frames/second and we send 50 back. The
# original per-sample Python loops (struct.pack_into, plus an inner exponent
# loop inside linear_to_ulaw) measured 17.1ms of CPU per second of call audio
# — about 1.7% of a fast core, but ~14% of the baseline budget on a 1/8-OCPU
# always-free VM. Vectorised, the same work costs 0.87ms/s (20x faster),
# which is negligible on any machine.
#
# Memory: 512 bytes for the decode table, 64 KB for encode. Build cost is a
# one-off ~0.2-1s at startup depending on the box.

_ULAW_DECODE_TABLE = np.array(
    [_ulaw2linear(b) for b in range(256)], dtype="<i2"
)
# Indexed by (sample + 32768) so the whole int16 range maps to an array offset.
_ULAW_ENCODE_TABLE = np.array(
    [linear_to_ulaw(s) for s in range(-32768, 32768)], dtype=np.uint8
)


def mulaw_to_pcm(mulaw_bytes: bytes) -> bytes:
    """Decode 8-bit mulaw audio to 16-bit linear PCM (little-endian).

    Twilio Media Streams sends one mulaw sample per byte.
    Output is two bytes per sample (int16 LE) at the same sample rate (8 kHz).
    """
    if not mulaw_bytes:
        return b""
    codes = np.frombuffer(mulaw_bytes, dtype=np.uint8)
    return _ULAW_DECODE_TABLE[codes].tobytes()


def pcm_to_mulaw(pcm_bytes: bytes) -> bytes:
    """Encode 16-bit linear PCM (little-endian, 8 kHz) to 8-bit mulaw."""
    usable = len(pcm_bytes) - (len(pcm_bytes) % 2)  # tolerate a trailing odd byte
    if usable == 0:
        return b""
    samples = np.frombuffer(pcm_bytes[:usable], dtype="<i2")
    return _ULAW_ENCODE_TABLE[samples.astype(np.int32) + 32768].tobytes()


def mp3_to_pcm8k(mp3_bytes: bytes) -> bytes:
    """Decode MP3 audio bytes to 16-bit signed LE mono PCM at 8 kHz using PyAV."""
    container = av.open(io.BytesIO(mp3_bytes))
    resampler = av.AudioResampler(format="s16", layout="mono", rate=8000)
    pcm_chunks = []
    for frame in container.decode(audio=0):
        resampled = resampler.resample(frame)
        for rf in resampled:
            pcm_chunks.append(rf.to_ndarray().tobytes())
    for rf in resampler.resample(None):
        pcm_chunks.append(rf.to_ndarray().tobytes())
    return b"".join(pcm_chunks)


def resample_8k_to_16k(pcm_8k: bytes) -> bytes:
    """Linear interpolation from 8 kHz → 16 kHz. Doubles the sample count.

    Each input sample is emitted as-is, followed by the midpoint between it and
    the next sample (the final sample is duplicated). Vectorised; produces
    byte-identical output to the original per-sample loop.
    """
    usable = len(pcm_8k) - (len(pcm_8k) % 2)
    if usable == 0:
        return b""
    samples = np.frombuffer(pcm_8k[:usable], dtype="<i2")
    n = samples.size

    # "Next" sample for each position; the last one pairs with itself.
    nxt = np.empty(n, dtype=np.int32)
    nxt[:-1] = samples[1:]
    nxt[-1] = samples[-1]

    # Floor division matches Python's `//` for negatives, as in the original.
    mid = (samples.astype(np.int32) + nxt) // 2

    out = np.empty(n * 2, dtype="<i2")
    out[0::2] = samples
    out[1::2] = mid.astype("<i2")
    return out.tobytes()


def _rms(pcm_8k: bytes) -> float:
    """RMS amplitude of int16 PCM (8 kHz), in int16 units."""
    usable = len(pcm_8k) - (len(pcm_8k) % 2)
    if usable == 0:
        return 0.0
    samples = np.frombuffer(pcm_8k[:usable], dtype="<i2").astype(np.float64)
    return float(np.sqrt(np.mean(samples * samples)))


# ---------- TwiML endpoint ----------

_TWIML_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Google.hi-IN-Standard-A">नमस्ते, वॉक्सफ़्लो में आपका स्वागत है।</Say>
  <Connect>
    <Stream url="wss://{host}/twilio/media" />
  </Connect>
</Response>"""


@router.post("/voice")
async def voice_webhook(request: Request) -> Response:
    """Return TwiML that opens a Media Streams connection back to this server."""
    client_ip = request.client.host if request.client else "unknown"
    if _rate_limited(client_ip):
        log.warning("twilio.rate_limited", ip=client_ip)
        raise HTTPException(status_code=429, detail="rate_limited")

    host = request.headers.get("host", "localhost:8000")
    if not re.match(r"^[\w\.\-]+(:\d+)?$", host):
        raise HTTPException(status_code=400, detail="invalid_host")

    form_dict: dict[str, Any] = {}
    try:
        form = await request.form()
        form_dict = {k: str(v) for k, v in form.items()}
    except Exception:
        pass

    if not _validate_twilio_signature(request, form_dict, "/twilio/voice"):
        log.warning("twilio.invalid_signature", ip=client_ip, call_sid=form_dict.get("CallSid", ""))
        raise HTTPException(status_code=403, detail="invalid_signature")

    call_sid = form_dict.get("CallSid", "")
    caller_phone = form_dict.get("From", "")
    to_number = form_dict.get("To", "")

    tenant_id = await _resolve_tenant(to_number)

    # Stash metadata for the WebSocket `start` event — Twilio's start payload
    # carries neither From nor To.
    if call_sid:
        _call_meta[call_sid] = {
            "caller_phone": caller_phone,
            "to_number": to_number,
            "tenant_id": tenant_id,
        }
    if len(_call_meta) > 1000:
        _call_meta.clear()  # entries are normally popped on `start`

    log.info("twilio.voice_webhook", call_sid=call_sid, from_=caller_phone, to=to_number, tenant_id=tenant_id)

    # Request call recording via Twilio REST API (non-blocking, skip during pytest)
    import os
    if call_sid and not os.environ.get("PYTEST_CURRENT_TEST"):
        async def _request_rec(url_base: str):
            try:
                from ..agent.tools import _get_twilio_client
                client = _get_twilio_client()
                if client:
                    callback_url = f"{url_base}/twilio/recording-callback"
                    await asyncio.to_thread(
                        client.calls(call_sid).recordings.create,
                        recording_status_callback=callback_url,
                        recording_status_callback_event=["completed"],
                    )
                    log.info("twilio.recording_requested", call_sid=call_sid)
            except Exception as e:
                log.warning("twilio.recording_request_failed", call_sid=call_sid, error=str(e))
        
        base_url = (get_settings().public_base_url or "").rstrip("/")
        if base_url:
            asyncio.create_task(_request_rec(base_url))

    # Prefer the configured public URL: behind a reverse proxy the Host header
    # is not necessarily the address Twilio can dial back on.
    base = (get_settings().public_base_url or "").rstrip("/")
    ws_host = base.split("://", 1)[-1] if base else host
    xml = _TWIML_TEMPLATE.replace("{host}", ws_host)
    return Response(
        content=xml,
        media_type="application/xml",
        headers={
            # Security hardening — Day 18 security pass.
            # TwiML is XML so browsers should never render or frame it.
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Cache-Control": "no-store, no-cache",
        },
    )


@router.post("/recording-callback")
async def recording_callback(request: Request) -> Response:
    """Webhook callback from Twilio when a call recording completes."""
    try:
        form = await request.form()
        call_sid = str(form.get("CallSid", ""))
        recording_url = str(form.get("RecordingUrl", ""))
        if recording_url and not recording_url.endswith(".mp3"):
            recording_url = f"{recording_url}.mp3"
        log.info("twilio.recording_received", call_sid=call_sid, url=recording_url)

        if call_sid and recording_url:
            # Update active in-memory session
            session = get_pipeline()._sessions.get(call_sid)
            if session:
                session.recording_url = recording_url

            # Update DB call record
            async with async_session_scope() as db:
                c = await db.get(Call, call_sid)
                if c:
                    c.recording_url = recording_url
                    await db.commit()
    except Exception as e:
        log.warning("twilio.recording_callback_error", error=str(e))

    return Response(content="<Response/>", media_type="application/xml")


# ---------- Media Streams WebSocket ----------


@dataclass
class _StreamState:
    """Per-connection state for one Twilio Media Stream call."""

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


async def _send_agent_audio(ws: WebSocket, st: _StreamState, agent_audio_b64: str) -> None:
    """Decode agent TTS MP3, encode to 8kHz mulaw, and stream paced frames to Twilio."""
    try:
        mp3_bytes = base64.b64decode(agent_audio_b64)
        pcm_8k = mp3_to_pcm8k(mp3_bytes)
        mulaw_bytes = pcm_to_mulaw(pcm_8k)

        # 20ms frame at 8kHz mulaw (1 byte per sample) = 160 bytes
        frame_size = 160
        total_bytes = len(mulaw_bytes)
        offset = 0

        log.info(
            "twilio.media.send_audio_start",
            call_sid=st.call_sid,
            stream_sid=st.stream_sid,
            pcm_len=len(pcm_8k),
            mulaw_len=total_bytes,
        )

        burst_frames = 3  # Initial 60ms lookahead burst
        while offset < total_bytes:
            chunk = mulaw_bytes[offset : offset + frame_size]
            offset += len(chunk)
            payload = base64.b64encode(chunk).decode("utf-8")
            msg = {
                "event": "media",
                "streamSid": st.stream_sid,
                "media": {"payload": payload},
            }
            await ws.send_text(json.dumps(msg))

            if burst_frames > 0:
                burst_frames -= 1
            else:
                await asyncio.sleep(0.02)

        log.info("twilio.media.send_audio_complete", call_sid=st.call_sid)
    except asyncio.CancelledError:
        # Barge-in: the caller started talking over the agent. Tell Twilio to
        # drop whatever it has already buffered so the agent stops mid-word.
        log.info("twilio.media.send_audio_cancelled", call_sid=st.call_sid)
        with contextlib.suppress(Exception, asyncio.CancelledError):
            clear_msg = {"event": "clear", "streamSid": st.stream_sid}
            await ws.send_text(json.dumps(clear_msg))
        # Re-raise so the task is correctly reported as cancelled rather than
        # completing normally — callers rely on that to know playback stopped.
        raise
    except Exception as e:
        log.error("twilio.media.send_audio_error", call_sid=st.call_sid, error=str(e))


async def _process_utterance(st: _StreamState, ws: WebSocket) -> None:
    """Flush the buffered utterance through STT -> agent -> TTS and stream audio back."""
    session = st.session
    if session is None:
        return
    try:
        result = await get_pipeline().commit_audio(session)
        if result.get("type") == "turn":
            log.info(
                "twilio.media.transcript",
                call_sid=st.call_sid,
                user_text=result["user_text"],
                agent_text=result["agent_text"],
                user_language=result.get("user_language"),
                user_confidence=result.get("user_confidence"),
            )
            st.last_turn = result
            agent_audio_b64 = result.get("agent_audio_b64")
            if agent_audio_b64:
                # Cancel existing send task if running (barge-in / next turn)
                if st.send_task and not st.send_task.done():
                    st.send_task.cancel()
                st.send_task = asyncio.create_task(_send_agent_audio(ws, st, agent_audio_b64))
    except Exception as e:
        log.error("twilio.media.processing_error", call_sid=st.call_sid, error=str(e))
    finally:
        st.processing = False


async def _finalize_stream(st: _StreamState | None) -> None:
    """Drain any in-flight utterance + leftover buffer, persist, clean up.

    Reaching `end_session()` is non-negotiable — it is what writes the call to
    Postgres and pushes the outcome row to Google Sheets. Nothing above it may
    be allowed to skip it.

    Note on `CancelledError`: it inherits from `BaseException`, not `Exception`.
    Awaiting a task we just cancelled therefore raises straight through a bare
    `except Exception`. That previously escaped this function and skipped
    persistence entirely — so any caller who hung up while the agent was
    speaking (a very common case) left no record of the call at all.
    """
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
                        "twilio.media.transcript_flush",
                        call_sid=st.call_sid,
                        user_text=result["user_text"],
                    )
            except Exception as e:
                log.error("twilio.media.final_flush_error", call_sid=st.call_sid, error=str(e))
    finally:
        # Always persist the call, whatever happened while draining above.
        try:
            await get_pipeline().end_session(st.call_sid, outcome="resolved")
        except Exception as e:
            log.error("twilio.media.end_session_failed", call_sid=st.call_sid, error=str(e))


@router.websocket("/media")
async def twilio_media_stream(ws: WebSocket) -> None:
    """WebSocket handler for Twilio Media Streams audio.

    Receives μ-law audio at 8 kHz, decodes to PCM, resamples to 16 kHz, buffers
    it per call, and on end-of-utterance (≥700ms of silence after speech) flushes
    the utterance into the STT -> agent -> TTS pipeline. Transcripts are logged
    and agent TTS audio is encoded and streamed back over the WebSocket.
    """
    # Rate-limit before accepting — close with 1008 (policy violation) if exceeded.
    client_ip = ws.client.host if ws.client else "unknown"
    if _ws_rate_limited(client_ip):
        log.warning("twilio.media.ws_rate_limited", ip=client_ip)
        await ws.accept()
        await ws.close(code=1008, reason="rate_limited")
        return

    await ws.accept()
    st: _StreamState | None = None

    log.info("twilio.media.connected")

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            event = msg.get("event")

            if event == "connected":
                log.info("twilio.media.connected_event")

            elif event == "start":
                start = msg.get("start", {})
                stream_sid = start.get("streamSid")
                call_sid = start.get("callSid")
                if not call_sid:
                    continue
                meta = _call_meta.pop(call_sid, {})
                session = get_pipeline().start_session(
                    caller_phone=meta.get("caller_phone", ""),
                    tenant_id=meta.get("tenant_id"),
                    call_id=call_sid,
                )
                st = _StreamState(
                    stream_sid=stream_sid,
                    call_sid=call_sid,
                    caller_phone=meta.get("caller_phone", ""),
                    session=session,
                )
                log.info(
                    "twilio.media.start",
                    stream_sid=stream_sid,
                    call_sid=call_sid,
                    tenant_id=session.tenant_id,
                )

            elif event == "media":
                if st is None or st.session is None:
                    continue
                payload = msg.get("media", {})
                b64_payload = payload.get("payload", "")
                if not b64_payload:
                    continue
                mulaw = base64.b64decode(b64_payload)
                pcm_8k = mulaw_to_pcm(mulaw)
                now = time.monotonic()

                rms = _rms(pcm_8k)
                if rms > _SILENCE_RMS:
                    st.speech = True
                    st.last_speech_at = now
                    # User speech barge-in: cancel active agent audio playback
                    if st.send_task and not st.send_task.done():
                        st.send_task.cancel()

                st.session.append_pcm(resample_8k_to_16k(pcm_8k))
                st.total_frames += 1
                st.total_bytes += len(mulaw)

                # ponytail: log every 100th frame; remove for production
                if st.total_frames % 100 == 0:
                    log.info(
                        "twilio.media.frame",
                        stream_sid=st.stream_sid,
                        frame_count=st.total_frames,
                        total_bytes=st.total_bytes,
                        mulaw_len=len(mulaw),
                        pcm_16k_len=len(pcm_8k) * 2,
                        rms=round(rms, 1),
                    )

                # End of utterance: heard speech, then ≥700ms of silence.
                if (
                    st.speech
                    and not st.processing
                    and (now - st.last_speech_at) * 1000 >= _SILENCE_MS
                ):
                    st.processing = True
                    st.task = asyncio.create_task(_process_utterance(st, ws))

            elif event == "stop":
                break

            elif event == "mark":
                pass

            else:
                log.debug("twilio.media.unknown_event", event=event)

    except WebSocketDisconnect:
        log.info("twilio.media.disconnected", frames=st.total_frames if st else 0)
    except Exception as e:
        log.error("twilio.media.error", error=str(e))
    finally:
        await _finalize_stream(st)
