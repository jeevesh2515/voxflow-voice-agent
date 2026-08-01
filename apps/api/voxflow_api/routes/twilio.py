"""Twilio Voice + Media Streams routes (Day 7-8).

Day 7: TwiML webhook + Media Streams WebSocket, mulaw->PCM decode, 8k->16k resample.
Day 8: buffers decoded PCM per call, detects utterance boundaries via a simple
amplitude VAD, and feeds completed utterances into the existing STT -> agent -> TTS
pipeline (voice/pipeline.py `commit_audio`). Transcripts are logged; streaming the
agent's TTS audio back is Day 9.
"""

from __future__ import annotations

import asyncio
import base64
import json
import math
import re
import struct
import time
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

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
_SILENCE_MS = 700

# CallSid -> caller metadata captured on the POST /voice webhook; the WebSocket
# `start` event consumes it (Twilio's start event carries no From/To).
_call_meta: dict[str, dict[str, str]] = {}


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


def mulaw_to_pcm(mulaw_bytes: bytes) -> bytes:
    """Decode 8-bit mulaw audio to 16-bit linear PCM (little-endian).

    Twilio Media Streams sends one mulaw sample per byte.
    Output is two bytes per sample (int16 LE) at the same sample rate (8 kHz).
    """
    pcm = bytearray(len(mulaw_bytes) * 2)
    for i, b in enumerate(mulaw_bytes):
        sample = _ulaw2linear(b)
        struct.pack_into("<h", pcm, i * 2, sample)
    return bytes(pcm)


def resample_8k_to_16k(pcm_8k: bytes) -> bytes:
    """Simple linear interpolation from 8 kHz → 16 kHz.

    Doubles sample count. For production, use a proper resampler (librosa /
    webrtcvad). This is good enough for Day 8.
    """
    n = len(pcm_8k) // 2
    out = bytearray(n * 4)
    for i in range(n):
        s0 = struct.unpack_from("<h", pcm_8k, i * 2)[0]
        # Insert interpolated sample at midpoint
        out[i * 4 : i * 4 + 2] = struct.pack("<h", s0)
        if i + 1 < n:
            s1 = struct.unpack_from("<h", pcm_8k, (i + 1) * 2)[0]
            mid = (s0 + s1) // 2
        else:
            mid = s0
        out[i * 4 + 2 : i * 4 + 4] = struct.pack("<h", mid)
    return bytes(out)


def _rms(pcm_8k: bytes) -> float:
    """RMS amplitude of int16 PCM (8 kHz), in int16 units."""
    n = len(pcm_8k) // 2
    if n == 0:
        return 0.0
    s = 0
    for i in range(n):
        v = struct.unpack_from("<h", pcm_8k, i * 2)[0]
        s += v * v
    return math.sqrt(s / n)


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
    """Return TwiML to open a Media Streams connection."""
    host = request.headers.get("host", "localhost:8000")
    # ponytail: simple hostname validation — only allow safe chars
    if not re.match(r"^[\w\.\-]+(:\d+)?$", host):
        raise HTTPException(status_code=400, detail="invalid_host")

    # Capture caller metadata so the WebSocket `start` event can build a CallSession.
    call_sid = ""
    caller_phone = ""
    try:
        form = await request.form()
        call_sid = str(form.get("CallSid") or "")
        caller_phone = str(form.get("From") or "")
    except Exception:
        pass
    if call_sid:
        _call_meta[call_sid] = {"caller_phone": caller_phone}
    if len(_call_meta) > 1000:
        _call_meta.clear()  # ponytail: cap; entries are popped on `start`

    xml = _TWIML_TEMPLATE.replace("{host}", host)
    return Response(content=xml, media_type="application/xml")


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
    last_turn: dict[str, Any] | None = None
    total_frames: int = 0
    total_bytes: int = 0


async def _process_utterance(st: _StreamState) -> None:
    """Flush the buffered utterance through STT -> agent -> TTS and log it."""
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
            # Day 9: encode agent_audio_b64 -> mulaw 8k and stream back.
            st.last_turn = result
    except Exception as e:
        log.error("twilio.media.processing_error", call_sid=st.call_sid, error=str(e))
    finally:
        st.processing = False


async def _finalize_stream(st: _StreamState | None) -> None:
    """Drain any in-flight utterance + leftover buffer, persist, clean up."""
    if st is None:
        return
    if st.task:
        try:
            await st.task
        except Exception:
            pass
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
    await get_pipeline().end_session(st.call_sid, outcome="resolved")


@router.websocket("/media")
async def twilio_media_stream(ws: WebSocket) -> None:
    """WebSocket handler for Twilio Media Streams audio.

    Receives μ-law audio at 8 kHz, decodes to PCM, resamples to 16 kHz, buffers
    it per call, and on end-of-utterance (≥700ms of silence after speech) flushes
    the utterance into the STT -> agent -> TTS pipeline. Transcripts are logged.
    """
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
                    call_id=call_sid,
                )
                st = _StreamState(
                    stream_sid=stream_sid,
                    call_sid=call_sid,
                    caller_phone=meta.get("caller_phone", ""),
                    session=session,
                )
                log.info("twilio.media.start", stream_sid=stream_sid, call_sid=call_sid)

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
                    st.task = asyncio.create_task(_process_utterance(st))

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
