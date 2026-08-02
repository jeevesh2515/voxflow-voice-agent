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

# Deterministic config before importing the app.
# Signature validation is exercised by its own tests below; the rest of the
# suite posts unsigned requests, so it is off by default here.
os.environ.setdefault("LLM_PROVIDER", "ollama")
os.environ.setdefault("DATABASE_URL", "sqlite:///./voxflow_test.db")
os.environ.setdefault("TWILIO_VALIDATE_SIGNATURE", "false")

from voxflow_api.routes.twilio import (  # noqa: E402
    _SILENCE_RMS,
    _rms,
    mulaw_to_pcm,
    resample_8k_to_16k,
)

# 0.25s 440Hz tone, mono 24kHz, encoded as MP3 — decodes to ~2000 samples at 8kHz.
_MP3_FIXTURE_B64 = (
    "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"
    "qqqq"
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
    """mp3_to_pcm8k must decode real MP3 bytes to 8kHz 16-bit mono PCM.

    Uses a checked-in MP3 fixture (0.25s 440Hz tone, 24kHz mono) rather than
    calling edge-tts over the network — the original version of this test hit
    Microsoft's servers, so it failed offline and in CI.
    """
    from voxflow_api.routes.twilio import mp3_to_pcm8k

    mp3_data = base64.b64decode(_MP3_FIXTURE_B64)
    assert len(mp3_data) > 0

    pcm = mp3_to_pcm8k(mp3_data)
    assert len(pcm) > 0
    # 16-bit samples -> even byte length
    assert len(pcm) % 2 == 0
    # 0.25s at 8kHz = ~2000 samples = ~4000 bytes. Allow codec padding slack.
    samples = len(pcm) // 2
    assert 1500 < samples < 3000, f"expected ~2000 samples at 8kHz, got {samples}"
    # A 440Hz tone must not decode to digital silence.
    assert _rms(pcm) > 100


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

        # Read an exact number of frames rather than looping until disconnect.
        #
        # Starlette's TestClient does not surface the server's close frame to
        # receive_text(), so a "read until it raises" loop blocks forever — that
        # is what used to hang this whole test suite. The frame count is
        # deterministic: mulaw is 1 byte per sample (PCM is 2), and the sender
        # emits 160-byte (20ms) frames.
        mulaw_len = len(fake_pcm) // 2
        expected_frames = math.ceil(mulaw_len / 160)
        for _ in range(expected_frames):
            msg = json.loads(ws.receive_text())
            if msg.get("event") == "media":
                outbound_msgs.append(msg)

        ws.send_text(json.dumps({"event": "stop"}))

    assert len(outbound_msgs) == expected_frames

    assert len(outbound_msgs) > 0
    assert outbound_msgs[0]["streamSid"] == "MX2"
    assert "payload" in outbound_msgs[0]["media"]



# ---------------------------------------------------------------------------
# Security + multi-tenancy (added with the customer-support call flow)
# ---------------------------------------------------------------------------


def test_signature_validation_rejects_unsigned_request(monkeypatch):
    """With validation on, an unsigned POST to /twilio/voice must be refused.

    /twilio/voice is public and unauthenticated. If it answers forged requests,
    anyone can drive the agent and burn the Groq/Twilio quota.
    """
    from fastapi.testclient import TestClient

    import voxflow_api.routes.twilio as tw
    from voxflow_api.config import get_settings
    from voxflow_api.main import create_app

    s = get_settings()
    monkeypatch.setattr(s, "twilio_validate_signature", True, raising=False)
    monkeypatch.setattr(s, "twilio_auth_token", "test_token_123", raising=False)
    tw._rate_buckets.clear()

    client = TestClient(create_app())
    r = client.post("/twilio/voice", data={"CallSid": "CA999", "From": "+15550001111"})
    assert r.status_code == 403


def test_signature_validation_accepts_correctly_signed_request(monkeypatch):
    """A request signed with the account auth token must be accepted."""
    from twilio.request_validator import RequestValidator

    from fastapi.testclient import TestClient

    import voxflow_api.routes.twilio as tw
    from voxflow_api.config import get_settings
    from voxflow_api.main import create_app

    token = "test_token_123"
    s = get_settings()
    monkeypatch.setattr(s, "twilio_validate_signature", True, raising=False)
    monkeypatch.setattr(s, "twilio_auth_token", token, raising=False)
    monkeypatch.setattr(s, "public_base_url", "https://voxflow.example.com", raising=False)
    tw._rate_buckets.clear()

    params = {"CallSid": "CA1000", "From": "+15550001111", "To": "+15550002222"}
    signature = RequestValidator(token).compute_signature(
        "https://voxflow.example.com/twilio/voice", params
    )

    client = TestClient(create_app())
    r = client.post("/twilio/voice", data=params, headers={"X-Twilio-Signature": signature})
    assert r.status_code == 200
    assert "<Stream url=" in r.text
    # The stream URL must point at the public host, not the internal one.
    assert "voxflow.example.com/twilio/media" in r.text


def test_rate_limiter_blocks_a_flood(monkeypatch):
    """The webhook must stop answering after the per-IP limit is exceeded."""
    from fastapi.testclient import TestClient

    import voxflow_api.routes.twilio as tw
    from voxflow_api.main import create_app

    tw._rate_buckets.clear()
    monkeypatch.setattr(tw, "_RATE_LIMIT_MAX", 5)

    client = TestClient(create_app())
    codes = [
        client.post("/twilio/voice", data={"CallSid": f"CA{i}", "From": "+1555"}).status_code
        for i in range(8)
    ]
    assert codes[:5] == [200] * 5
    assert codes[5:] == [429] * 3
    tw._rate_buckets.clear()


def test_unmapped_number_falls_back_to_default_tenant():
    """An unknown dialed number resolves to the configured default tenant."""
    import asyncio

    import voxflow_api.routes.twilio as tw
    from voxflow_api.config import get_settings

    resolved = asyncio.run(tw._resolve_tenant("+19998887777"))
    assert resolved == get_settings().default_tenant_id


def test_mapped_number_resolves_to_its_own_tenant():
    """A number in tenant_phone_numbers routes the call to that tenant.

    This is what stops company A's caller reaching company B's order data.
    """
    import asyncio

    import voxflow_api.routes.twilio as tw
    from voxflow_api.db import Tenant, TenantPhoneNumber, init_db, session_scope

    init_db()
    with session_scope() as db:
        if not db.get(Tenant, "acme"):
            db.add(Tenant(id="acme", name="Acme Foods"))
        if not db.get(TenantPhoneNumber, "+14155550123"):
            db.add(
                TenantPhoneNumber(
                    phone_number="+14155550123", tenant_id="acme", label="Acme support line"
                )
            )

    assert asyncio.run(tw._resolve_tenant("+14155550123")) == "acme"
