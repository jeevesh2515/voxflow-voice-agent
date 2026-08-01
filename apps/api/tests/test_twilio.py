"""Tests for Twilio routes: mulaw decode, resample, VAD, TwiML webhook (Day 8)."""

import base64
import json
import math
import os
import struct
import sys
import time
from pathlib import Path

# Ensure we can import voxflow_api when running `pytest` from apps/api/
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Deterministic config before importing the app
os.environ.setdefault("LLM_PROVIDER", "ollama")
os.environ.setdefault("DATABASE_URL", "sqlite:///./voxflow_test.db")

from voxflow_api.routes.twilio import (  # noqa: E402
    _SILENCE_RMS,
    _rms,
    mulaw_to_pcm,
    resample_8k_to_16k,
)


def _sine(amp: int, n: int, freq_hz: int = 1000, rate: int = 8000) -> bytes:
    return struct.pack(
        "<%dh" % n,
        *[int(amp * math.sin(2 * math.pi * freq_hz * i / rate)) for i in range(n)],
    )


def test_mulaw_silence_decodes_to_zero():
    # 0xFF is the μ-law zero/silence codeword -> must decode to 0, not a DC offset.
    pcm = mulaw_to_pcm(b"\xff" * 40)
    assert len(pcm) == 80
    assert all(struct.unpack_from("<h", pcm, i * 2)[0] == 0 for i in range(40))


def test_mulaw_to_pcm_length():
    assert len(mulaw_to_pcm(b"\x00" * 10)) == 20


def test_mulaw_smallest_positive_step():
    # 0xFE is the smallest positive level (~8 in int16 units).
    assert struct.unpack_from("<h", mulaw_to_pcm(b"\xfe"), 0)[0] == 8


def test_mulaw_extremes_stay_in_int16_range():
    # Loudest samples must not overflow 16-bit.
    for b in (0x00, 0x7F, 0x80, 0xFF):
        v = struct.unpack_from("<h", mulaw_to_pcm(bytes([b])), 0)[0]
        assert -32768 <= v <= 32767


def test_resample_doubles_length_and_keeps_first_sample():
    src = struct.pack("<10h", *range(10))
    out = resample_8k_to_16k(src)
    assert len(out) == 40  # 20 samples * 2 bytes
    assert struct.unpack_from("<h", out, 0)[0] == 0  # first sample preserved
    # Midpoint is the linear average of adjacent samples.
    assert struct.unpack_from("<h", out, 2)[0] == 0


def test_rms_silence_vs_speech():
    assert _rms(b"\x00\x00" * 160) == 0.0
    # 1 kHz sine, amplitude 16000 -> RMS ~11314, well above the silence threshold.
    assert _rms(_sine(16000, 160)) > _SILENCE_RMS


def test_voice_webhook_returns_twiml():
    from fastapi.testclient import TestClient

    from voxflow_api.main import create_app

    client = TestClient(create_app())
    r = client.post(
        "/twilio/voice",
        data={"CallSid": "CA123", "From": "+919876543210"},
    )
    assert r.status_code == 200
    body = r.text
    assert "<Stream url=" in body
    assert "/twilio/media" in body


class _FakePipeline:
    """Stand-in for VoicePipeline — records flushes without loading whisper/LLM."""

    def __init__(self) -> None:
        self.starts: list[dict] = []
        self.commits: list[dict] = []
        self.ends: list[dict] = []

    def start_session(self, caller_phone="", caller_name="", language=None, tenant_id=None, call_id=None):
        from voxflow_api.voice.pipeline import CallSession

        self.starts.append({"call_id": call_id, "caller_phone": caller_phone})
        return CallSession(call_id=call_id or "call_x", caller_phone=caller_phone)

    async def commit_audio(self, session):
        self.commits.append({"call_id": session.call_id, "pcm_bytes": len(session.pcm_buffer)})
        session.reset_pcm()
        return {
            "type": "turn",
            "user_text": "मुझे 50 केस चाहिए",
            "agent_text": "ठीक है",
            "user_language": "hi",
            "user_confidence": 0.9,
        }

    async def end_session(self, call_id, outcome="resolved"):
        self.ends.append({"call_id": call_id, "outcome": outcome})


def test_media_stream_flushes_utterance_on_silence(monkeypatch):
    """Speech frames -> 700ms (patched to 50ms) of silence -> STT flush -> session end."""
    from fastapi.testclient import TestClient

    import voxflow_api.routes.twilio as tw
    from voxflow_api.main import create_app

    fp = _FakePipeline()
    monkeypatch.setattr(tw, "get_pipeline", lambda: fp)
    monkeypatch.setattr(tw, "_SILENCE_MS", 50)

    # 0x00 mulaw = loud negative level; 0xFF = silence.
    speech_b64 = base64.b64encode(b"\x00" * 160).decode()
    silence_b64 = base64.b64encode(b"\xff" * 160).decode()

    client = TestClient(create_app())
    # Webhook carries the caller's phone; the WS start event must pick it up.
    r = client.post("/twilio/voice", data={"CallSid": "CA123", "From": "+919876543210"})
    assert r.status_code == 200

    with client.websocket_connect("/twilio/media") as ws:
        ws.send_text(json.dumps({"event": "connected"}))
        ws.send_text(
            json.dumps(
                {"event": "start", "start": {"streamSid": "MX1", "callSid": "CA123"}}
            )
        )
        for _ in range(20):
            ws.send_text(
                json.dumps({"event": "media", "media": {"payload": speech_b64}})
            )
        time.sleep(0.08)  # let trailing-silence window elapse
        ws.send_text(
            json.dumps({"event": "media", "media": {"payload": silence_b64}})
        )
        time.sleep(0.08)
        ws.send_text(json.dumps({"event": "stop"}))

    # CallSession wired from callSid + caller phone from the webhook.
    assert fp.starts[0] == {"call_id": "CA123", "caller_phone": "+919876543210"}
    # At least one utterance flushed with actual audio in the buffer.
    assert any(c["call_id"] == "CA123" and c["pcm_bytes"] > 0 for c in fp.commits)
    # Session ended on stop.
    assert fp.ends[0] == {"call_id": "CA123", "outcome": "resolved"}


def test_linear_to_ulaw_roundtrip():
    """Verify linear_to_ulaw preserves all G.711 PCM quantization points."""
    from voxflow_api.routes.twilio import _ulaw2linear, linear_to_ulaw

    for b in range(256):
        pcm = _ulaw2linear(b)
        re_b = linear_to_ulaw(pcm)
        re_pcm = _ulaw2linear(re_b)
        assert re_pcm == pcm


def test_mp3_to_pcm8k_decodes_audio():
    """Test mp3_to_pcm8k decoding using PyAV."""
    import asyncio
    import edge_tts
    from voxflow_api.routes.twilio import mp3_to_pcm8k

    async def _gen_mp3():
        tts = edge_tts.Communicate("Hello", "en-IN-NeerjaNeural")
        buf = bytearray()
        async for chunk in tts.stream():
            if chunk["type"] == "audio":
                buf.extend(chunk["data"])
        return bytes(buf)

    mp3_data = asyncio.run(_gen_mp3())
    assert len(mp3_data) > 0

    pcm = mp3_to_pcm8k(mp3_data)
    assert len(pcm) > 0
    # Must be 16-bit mono PCM (even byte length)
    assert len(pcm) % 2 == 0


def test_media_stream_sends_outbound_audio(monkeypatch):
    """Verify WebSocket handler streams outbound media frames when turn returns agent_audio_b64."""
    from fastapi.testclient import TestClient
    import voxflow_api.routes.twilio as tw
    from voxflow_api.main import create_app

    # Create a tiny 160-byte mulaw payload as fake agent_audio_b64
    fake_pcm = b"\x00\x00" * 80  # 80 samples 8kHz PCM = 10ms
    fake_mp3_b64 = base64.b64encode(b"fake_mp3").decode()

    class _OutboundPipeline(_FakePipeline):
        async def commit_audio(self, session):
            return {
                "type": "turn",
                "user_text": "hello",
                "agent_text": "hi there",
                "agent_audio_b64": fake_mp3_b64,
            }

    fp = _OutboundPipeline()
    monkeypatch.setattr(tw, "get_pipeline", lambda: fp)
    monkeypatch.setattr(tw, "_SILENCE_MS", 20)
    monkeypatch.setattr(tw, "mp3_to_pcm8k", lambda mp3_b: fake_pcm)

    speech_b64 = base64.b64encode(b"\x00" * 160).decode()
    silence_b64 = base64.b64encode(b"\xff" * 160).decode()

    client = TestClient(create_app())
    client.post("/twilio/voice", data={"CallSid": "CA456", "From": "+919876543210"})

    outbound_msgs = []

    with client.websocket_connect("/twilio/media") as ws:
        ws.send_text(json.dumps({"event": "connected"}))
        ws.send_text(
            json.dumps({"event": "start", "start": {"streamSid": "MX2", "callSid": "CA456"}})
        )
        ws.send_text(json.dumps({"event": "media", "media": {"payload": speech_b64}}))
        time.sleep(0.05)
        ws.send_text(json.dumps({"event": "media", "media": {"payload": silence_b64}}))
        time.sleep(0.1)

        # Receive outbound media frames sent back by server
        while True:
            try:
                raw = ws.receive_text()
                msg = json.loads(raw)
                if msg.get("event") == "media":
                    outbound_msgs.append(msg)
            except Exception:
                break

    assert len(outbound_msgs) > 0
    assert outbound_msgs[0]["streamSid"] == "MX2"
    assert "payload" in outbound_msgs[0]["media"]

