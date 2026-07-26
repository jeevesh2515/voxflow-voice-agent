"""Twilio Voice + Media Streams routes (Day 7)."""

from __future__ import annotations

import base64
import json
import re
import struct

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

from ..logging import get_logger


log = get_logger(__name__)
router = APIRouter(prefix="/twilio", tags=["twilio"])


# ---------- mulaw / PCM utilities ----------

def mulaw_to_pcm(mulaw_bytes: bytes) -> bytes:
    """Decode 8-bit mulaw audio to 16-bit linear PCM (little-endian).

    Twilio Media Streams sends one mulaw sample per byte.
    Output is two bytes per sample (int16 LE) at the same sample rate (8 kHz).
    """
    pcm = bytearray(len(mulaw_bytes) * 2)
    for i, b in enumerate(mulaw_bytes):
        # Standard mulaw -> linear expansion
        sample = _ulaw2linear(b)
        struct.pack_into("<h", pcm, i * 2, sample)
    return bytes(pcm)


def _ulaw2linear(ulaw_byte: int) -> int:
    """Expand one 8-bit μ-law byte to 16-bit signed linear PCM."""
    ulaw_byte = ~ulaw_byte & 0xFF
    sign = ulaw_byte & 0x80
    exponent = (ulaw_byte >> 4) & 0x07
    mantissa = ulaw_byte & 0x0F
    sample = ((mantissa << 3) + 0x84) << (exponent + 2)
    if sign:
        sample = -sample
    return sample


def resample_8k_to_16k(pcm_8k: bytes) -> bytes:
    """Simple linear interpolation from 8 kHz → 16 kHz.

    Doubles sample count. For production, use a proper resampler (librosa /
    webrtcvad). This is good enough for Day 7.
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
    xml = _TWIML_TEMPLATE.replace("{host}", host)
    return Response(content=xml, media_type="application/xml")


# ---------- Media Streams WebSocket ----------

@router.websocket("/media")
async def twilio_media_stream(ws: WebSocket) -> None:
    """WebSocket handler for Twilio Media Streams audio.

    Receives μ-law audio frames at 8 kHz, decodes to PCM, and logs
    frame statistics. Later days will wire STT / pipeline processing.
    """
    await ws.accept()
    stream_sid: str | None = None
    call_sid: str | None = None
    frame_count = 0
    total_bytes = 0

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
                log.info("twilio.media.start", stream_sid=stream_sid, call_sid=call_sid)

            elif event == "media":
                payload = msg.get("media", {})
                b64_payload = payload.get("payload", "")
                if not b64_payload:
                    continue
                mulaw = base64.b64decode(b64_payload)
                pcm_8k = mulaw_to_pcm(mulaw)
                pcm_16k = resample_8k_to_16k(pcm_8k)
                frame_count += 1
                total_bytes += len(mulaw)

                # ponytail: log every 100th frame; remove for production
                if frame_count % 100 == 0:
                    log.info(
                        "twilio.media.frame",
                        stream_sid=stream_sid,
                        frame_count=frame_count,
                        total_bytes=total_bytes,
                        mulaw_len=len(mulaw),
                        pcm_16k_len=len(pcm_16k),
                    )

            elif event == "stop":
                stop = msg.get("stop", {})
                log.info(
                    "twilio.media.stop",
                    stream_sid=stream_sid or stop.get("streamSid"),
                    call_sid=call_sid or stop.get("callSid"),
                    total_frames=frame_count,
                    total_bytes=total_bytes,
                )
                break

            elif event == "mark":
                pass

            else:
                log.debug("twilio.media.unknown_event", event=event)

    except WebSocketDisconnect:
        log.info("twilio.media.disconnected", frames=frame_count)
    except Exception as e:
        log.error("twilio.media.error", error=str(e))
