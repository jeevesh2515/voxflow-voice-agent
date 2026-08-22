"""Tests for Telnyx Voice + Media Streams routes."""

from __future__ import annotations

import base64
import json
import os

import pytest
from fastapi.testclient import TestClient

from voxflow_api.main import create_app
import voxflow_api.routes.telnyx as tx
from voxflow_api.telephony.registry import get_telephony_provider


@pytest.fixture
def client():
    return TestClient(create_app())


class _FakePipeline:
    def __init__(self) -> None:
        self.starts: list[dict] = []
        self.commits: list[dict] = []
        self.ends: list[dict] = []

    def start_session(self, caller_phone="", caller_name="", language=None, tenant_id=None, call_id=None):
        from voxflow_api.voice.pipeline import CallSession

        self.starts.append({"call_id": call_id, "caller_phone": caller_phone, "tenant_id": tenant_id})
        return CallSession(call_id=call_id or "call_tx", caller_phone=caller_phone, tenant_id=tenant_id or "varun")

    async def commit_audio(self, session):
        self.commits.append({"call_id": session.call_id, "pcm_bytes": len(session.pcm_buffer)})
        session.reset_pcm()
        return {
            "type": "turn",
            "user_text": "Need order update",
            "agent_text": "Sure, checking",
            "user_language": "en",
            "user_confidence": 0.95,
        }

    async def end_session(self, call_id, outcome="resolved"):
        self.ends.append({"call_id": call_id, "outcome": outcome})


def test_telnyx_voice_webhook_texml(client):
    r = client.post(
        "/telnyx/voice",
        data={"CallSid": "tx_123", "From": "+14155550100", "To": "+14155550200"},
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/xml")
    body = r.text
    assert "<Stream url=" in body
    assert "/telnyx/media" in body


def test_telnyx_voice_webhook_json(client):
    payload = {
        "data": {
            "event_type": "call.initiated",
            "payload": {
                "call_control_id": "v2_call_999",
                "from": "+919876543210",
                "to": "+14155550200",
            },
        }
    }
    r = client.post("/telnyx/voice", json=payload)
    assert r.status_code == 200
    assert "/telnyx/media" in r.text


def test_telnyx_status_callback(client):
    r = client.post("/telnyx/status", json={"data": {"event_type": "call.hangup"}})
    assert r.status_code == 200


def test_telnyx_media_stream_lifecycle(monkeypatch, client):
    fp = _FakePipeline()
    monkeypatch.setattr(tx, "get_pipeline", lambda: fp)
    monkeypatch.setattr(tx, "_SILENCE_MS", 50)

    # Prime call metadata
    client.post("/telnyx/voice", data={"CallSid": "TX_CALL_1", "From": "+15551234567"})

    speech_b64 = base64.b64encode(b"\x00" * 160).decode()
    silence_b64 = base64.b64encode(b"\xff" * 160).decode()

    with client.websocket_connect("/telnyx/media") as ws:
        ws.send_text(json.dumps({"event": "connected"}))
        ws.send_text(
            json.dumps(
                {"event": "start", "start": {"streamSid": "STR_1", "callSid": "TX_CALL_1"}}
            )
        )
        for _ in range(10):
            ws.send_text(
                json.dumps({"event": "media", "media": {"payload": speech_b64}})
            )
        for _ in range(10):
            ws.send_text(
                json.dumps({"event": "media", "media": {"payload": silence_b64}})
            )
        ws.send_text(json.dumps({"event": "stop"}))

    assert len(fp.starts) == 1
    assert fp.starts[0]["call_id"] == "TX_CALL_1"
    assert fp.starts[0]["caller_phone"] == "+15551234567"
    assert len(fp.ends) == 1
    assert fp.ends[0]["call_id"] == "TX_CALL_1"
