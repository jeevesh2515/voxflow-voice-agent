"""Tests for Amazon Connect call recording ingestion and UK GDPR consent persistence."""

from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from voxflow_api.config import get_settings
from voxflow_api.db import (
    Call,
    RecipientCampaignPreference,
    async_session_scope,
    reset_db,
    session_scope,
)
from voxflow_api.main import create_app
from voxflow_api.seed import seed
from voxflow_api.services.recording_service import (
    build_consent_evidence,
    persist_recording_and_consent,
)

_S3_HANDLER_PATH = (
    Path(__file__).resolve().parents[3] / "deploy" / "aws" / "s3_recordings_handler.py"
)
_SIGNING_SECRET = "test_connect_secret_987"


@pytest.fixture(scope="module")
def s3_handler_module():
    """Import s3_recordings_handler by path."""
    if not _S3_HANDLER_PATH.exists():
        pytest.skip(f"s3_recordings_handler.py not found at {_S3_HANDLER_PATH}")
    spec = importlib.util.spec_from_file_location("voxflow_s3_handler", _S3_HANDLER_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _json_body(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _signed_headers(
    body: bytes,
    *,
    timestamp: str | None = None,
    path: str = "/api/connect/recording",
    secret: str = _SIGNING_SECRET,
) -> dict[str, str]:
    timestamp = timestamp or str(time.time())
    message = timestamp.encode("utf-8") + b":" + path.encode("utf-8") + b":" + body
    signature = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return {
        "content-type": "application/json",
        "x-voxflow-signature": signature,
        "x-voxflow-timestamp": timestamp,
    }


@pytest.fixture
def client(monkeypatch):
    settings = get_settings()
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setattr(settings, "connect_lambda_secret", _SIGNING_SECRET, raising=False)
    monkeypatch.setattr(settings, "provider_callback_shared_secret", _SIGNING_SECRET, raising=False)
    monkeypatch.setattr(settings, "provider_callback_validate_signature", True)
    monkeypatch.setattr(settings, "sentry_environment", "development")

    reset_db()
    seed(reset=True)
    with TestClient(create_app()) as test_client:
        yield test_client


# =====================================================================
# 1. S3 Lambda Handler Unit Tests
# =====================================================================


def test_extract_contact_id_uuid(s3_handler_module):
    uuid_key = "connect/instance-1/2026/09/04/a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d/audio.wav"
    assert s3_handler_module._extract_contact_id(uuid_key) == "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d"


def test_extract_contact_id_fallback_path(s3_handler_module):
    custom_key = "connect/instance-1/2026/09/04/custom_contact_123/audio.wav"
    assert s3_handler_module._extract_contact_id(custom_key) == "custom_contact_123"


def test_extract_contact_id_invalid(s3_handler_module):
    invalid_key = "connect/instance-1/no_date/audio.wav"
    assert s3_handler_module._extract_contact_id(invalid_key) is None


def test_is_recording_key_extensions(s3_handler_module):
    assert s3_handler_module._is_recording_key("connect/inst/2026/09/04/c1/audio.wav")
    assert s3_handler_module._is_recording_key("connect/inst/2026/09/04/c1/AUDIO.MP3")
    assert s3_handler_module._is_recording_key("connect/inst/2026/09/04/c1/audio.flac")
    assert s3_handler_module._is_recording_key("connect/inst/2026/09/04/c1/audio.ogg")
    assert not s3_handler_module._is_recording_key("connect/inst/2026/09/04/c1/audio.txt")
    assert not s3_handler_module._is_recording_key("other/path/audio.wav")


def test_s3_handler_sign_request(s3_handler_module):
    secret = "my_secret"
    ts = "1725430000.0"
    path = "/api/connect/recording"
    body = b'{"hello":"world"}'
    sig = s3_handler_module._sign_request(secret, ts, path, body)
    expected = hmac.new(b"my_secret", ts.encode() + b":" + path.encode() + b":" + body, hashlib.sha256).hexdigest()
    assert sig == expected


def test_s3_lambda_handler_execution(s3_handler_module, monkeypatch):
    monkeypatch.setenv("VOXFLOW_API_URL", "https://api.voxflow.test")
    monkeypatch.setenv("VOXFLOW_SECRET", _SIGNING_SECRET)
    monkeypatch.setenv("CONNECT_INSTANCE_ID", "inst-uk-1")
    monkeypatch.setenv("CONNECT_REGION", "eu-west-2")

    posted_calls = []

    def mock_post_json(url, payload, secret, path, **kwargs):
        posted_calls.append({"url": url, "payload": payload, "secret": secret, "path": path})
        return {"ok": True, "persisted": True}

    monkeypatch.setattr(s3_handler_module, "_post_json", mock_post_json)

    mock_connect = MagicMock()
    mock_connect.get_contact_attributes.return_value = {
        "Attributes": {
            "consent_granted": "true",
            "consent_recorded": "true",
        }
    }
    mock_s3 = MagicMock()

    mock_boto3 = MagicMock()
    mock_boto3.client.side_effect = lambda service, **kwargs: mock_connect if service == "connect" else mock_s3
    monkeypatch.setattr("boto3.client", mock_boto3.client)

    event = {
        "Records": [
            {
                "eventSource": "aws:s3",
                "s3": {
                    "bucket": {"name": "amazon-connect-recordings-london"},
                    "object": {"key": "connect/inst-uk-1/2026/09/04/c1234567-89ab-cdef-0123-456789abcdef/call_audio.wav"},
                },
            }
        ]
    }

    res = s3_handler_module.lambda_handler(event, None)
    assert res == {"statusCode": 200, "handled": 1}

    mock_connect.get_contact_attributes.assert_called_once_with(
        InstanceId="inst-uk-1",
        InitialContactId="c1234567-89ab-cdef-0123-456789abcdef",
    )
    mock_s3.put_object_tagging.assert_called_once()
    tag_call = mock_s3.put_object_tagging.call_args[1]
    tags = {t["Key"]: t["Value"] for t in tag_call["Tagging"]["TagSet"]}
    assert tags["voxflow:consent"] == "true"
    assert tags["voxflow:recorded"] == "true"
    assert tags["voxflow:contact-id"] == "c1234567-89ab-cdef-0123-456789abcdef"
    assert "voxflow:retention-until" in tags

    assert len(posted_calls) == 1
    p = posted_calls[0]["payload"]
    assert p["contact_id"] == "c1234567-89ab-cdef-0123-456789abcdef"
    assert p["bucket"] == "amazon-connect-recordings-london"
    assert p["recording_url"] == "s3://amazon-connect-recordings-london/connect/inst-uk-1/2026/09/04/c1234567-89ab-cdef-0123-456789abcdef/call_audio.wav"
    assert p["consent_granted"] is True
    assert p["consent_recorded"] is True


# =====================================================================
# 2. Recording Persistence Service Tests
# =====================================================================


def test_build_consent_evidence():
    ts = datetime(2026, 9, 4, 12, 0, 0, tzinfo=timezone.utc)
    ev = build_consent_evidence(
        region="eu-west-2",
        instance_id="inst-1",
        contact_id="cont-1",
        consent_granted=True,
        consent_recorded=True,
        ts=ts,
    )
    assert ev == "connect:eu-west-2:inst-1:cont-1:consent=granted:recorded=yes:at=2026-09-04T12:00:00+00:00"

    ev_denied = build_consent_evidence(
        region="eu-west-2",
        instance_id="inst-1",
        contact_id="cont-1",
        consent_granted=False,
        consent_recorded=True,
        ts=ts,
    )
    assert ev_denied == "connect:eu-west-2:inst-1:cont-1:consent=denied:recorded=yes:at=2026-09-04T12:00:00+00:00"


@pytest.mark.asyncio
async def test_persist_recording_validation_errors():
    with pytest.raises(ValueError, match="contact_id and s3_key are required"):
        await persist_recording_and_consent({"contact_id": "", "s3_key": "k"})

    with pytest.raises(ValueError, match="contact_id and s3_key are required"):
        await persist_recording_and_consent({"contact_id": "c", "s3_key": ""})


@pytest.mark.asyncio
async def test_persist_recording_consent_not_recorded():
    res = await persist_recording_and_consent({
        "contact_id": "c-unrecorded",
        "s3_key": "k",
        "consent_recorded": False,
    })
    assert res == {"persisted": True, "reason": "consent_not_recorded", "evidence_ref": ""}


@pytest.mark.asyncio
async def test_persist_recording_call_not_found():
    reset_db()
    seed(reset=True)
    res = await persist_recording_and_consent({
        "contact_id": "c-nonexistent",
        "s3_key": "connect/inst/2026/09/04/c-nonexistent/audio.wav",
        "bucket": "test-bucket",
        "consent_recorded": True,
        "consent_granted": True,
    })
    assert res == {"persisted": False, "reason": "call_not_found", "evidence_ref": ""}


@pytest.mark.asyncio
async def test_persist_recording_success_and_recipient_preference():
    reset_db()
    seed(reset=True)

    # Insert a test Call row
    contact_id = "test-contact-recording-1"
    caller_phone = "+447700900123"
    with session_scope() as sync_db:
        call = Call(
            id=contact_id,
            tenant_id="varun",
            caller_phone=caller_phone,
            intent="order_status",
            reason="Where is my order?",
        )
        sync_db.add(call)
        sync_db.commit()

    # Persist recording with consent granted
    payload = {
        "contact_id": contact_id,
        "bucket": "connect-recordings-bucket",
        "s3_key": f"connect/inst-1/2026/09/04/{contact_id}/rec.wav",
        "recording_url": f"s3://connect-recordings-bucket/connect/inst-1/2026/09/04/{contact_id}/rec.wav",
        "instance_id": "inst-1",
        "region": "eu-west-2",
        "consent_granted": True,
        "consent_recorded": True,
    }

    res = await persist_recording_and_consent(payload)
    assert res["persisted"] is True
    assert res["reason"] == "ok"
    assert "connect:eu-west-2:inst-1:test-contact-recording-1:consent=granted:recorded=yes:at=" in res["evidence_ref"]

    # Verify DB state
    async with async_session_scope() as db:
        saved_call = await db.get(Call, contact_id)
        assert saved_call is not None
        assert saved_call.recording_url == payload["recording_url"]
        assert saved_call.recording_s3_key == payload["s3_key"]
        assert saved_call.consent_granted == 1
        assert saved_call.consent_recorded_at is not None
        assert saved_call.consent_evidence_ref == res["evidence_ref"]

    # Verify RecipientCampaignPreference was created
    with session_scope() as sync_db:
        pref = (
            sync_db.query(RecipientCampaignPreference)
            .filter_by(tenant_id="varun", recipient_phone=caller_phone)
            .one_or_none()
        )
        assert pref is not None
        assert pref.consent_status == "granted"
        assert pref.consent_purpose == "inbound_call_recording"
        assert pref.opted_out == 0
        assert pref.source == "connect_ivr_consent"

    # Idempotency check: submitting the exact same payload should return already_persisted
    res_again = await persist_recording_and_consent(payload)
    assert res_again["persisted"] is True
    assert res_again["reason"] == "already_persisted"
    assert res_again["evidence_ref"] == res["evidence_ref"]


# =====================================================================
# 3. FastAPI Route Tests (POST /api/connect/recording)
# =====================================================================


def test_api_connect_recording_rejects_missing_signature(client):
    body = _json_body({"contact_id": "c1"})
    resp = client.post(
        "/api/connect/recording",
        content=body,
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "invalid_signature"


def test_api_connect_recording_rejects_tampered_signature(client):
    body = _json_body({"contact_id": "c1"})
    headers = _signed_headers(body, secret="wrong_secret")
    resp = client.post("/api/connect/recording", content=body, headers=headers)
    assert resp.status_code == 403
    assert resp.json()["detail"] == "invalid_signature"


def test_api_connect_recording_rejects_stale_timestamp(client):
    body = _json_body({"contact_id": "c1"})
    # 2 hours in the past
    stale_ts = str(time.time() - 7200)
    headers = _signed_headers(body, timestamp=stale_ts)
    resp = client.post("/api/connect/recording", content=body, headers=headers)
    assert resp.status_code == 403
    assert resp.json()["detail"] == "invalid_signature"


def test_api_connect_recording_404_on_unknown_call(client):
    body_dict = {
        "contact_id": "unknown-call-id-999",
        "bucket": "b",
        "s3_key": "connect/inst/2026/09/04/unknown-call-id-999/audio.wav",
        "consent_recorded": True,
        "consent_granted": True,
    }
    body = _json_body(body_dict)
    headers = _signed_headers(body)
    resp = client.post("/api/connect/recording", content=body, headers=headers)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "call_not_found"


def test_api_connect_recording_success_end_to_end(client):
    contact_id = "test-api-recording-call"
    with session_scope() as sync_db:
        call = Call(
            id=contact_id,
            tenant_id="varun",
            caller_phone="+447700900999",
            intent="pricing_inquiry",
            reason="Asking for quote",
        )
        sync_db.add(call)
        sync_db.commit()

    body_dict = {
        "contact_id": contact_id,
        "bucket": "amazon-connect-bucket-london",
        "s3_key": f"connect/inst-london/2026/09/04/{contact_id}/rec.flac",
        "instance_id": "inst-london",
        "region": "eu-west-2",
        "consent_recorded": True,
        "consent_granted": True,
    }
    body = _json_body(body_dict)
    headers = _signed_headers(body)
    resp = client.post("/api/connect/recording", content=body, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["contact_id"] == contact_id
    assert data["persisted"] is True
    assert f"connect:eu-west-2:inst-london:{contact_id}:consent=granted:recorded=yes:at=" in data["evidence_ref"]

    # Verify persisted in database
    with session_scope() as sync_db:
        c = sync_db.query(Call).filter_by(id=contact_id).one()
        assert c.recording_url == f"s3://amazon-connect-bucket-london/connect/inst-london/2026/09/04/{contact_id}/rec.flac"
        assert c.recording_s3_key == f"connect/inst-london/2026/09/04/{contact_id}/rec.flac"
        assert c.consent_granted == 1
        assert c.consent_evidence_ref == data["evidence_ref"]
