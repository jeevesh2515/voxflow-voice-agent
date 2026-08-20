"""Day 33 end-to-end fixture certification for the Dial sandbox callback adapter."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from voxflow_api.config import get_settings
from voxflow_api.db import (
    CampaignQueue,
    JobRun,
    OutboundCampaign,
    ProviderCallbackAdapterAudit,
    ProviderEvent,
    ProviderOperation,
    SessionLocal,
    reset_db,
)
from voxflow_api.main import create_app
from voxflow_api.seed import seed


DIAL_SECRET_CURRENT = "day33-dial-current-secret"
DIAL_SECRET_PREVIOUS = "day33-dial-previous-secret"
CALL_ID = "call_dial_sandbox_001"
NOW = datetime.now(timezone.utc).replace(microsecond=0)


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _configure_adapter(monkeypatch, *, allowed_tenants: str = "varun", secrets: str | None = None) -> None:
    monkeypatch.setenv("DIAL_CALLBACK_ADAPTER_ENABLED", "true")
    monkeypatch.setenv("DIAL_CALLBACK_SANDBOX_MODE", "true")
    monkeypatch.setenv("DIAL_CALLBACK_ALLOWED_TENANTS", allowed_tenants)
    monkeypatch.setenv("DIAL_CALLBACK_SIGNING_SECRETS", secrets or f"{DIAL_SECRET_CURRENT},{DIAL_SECRET_PREVIOUS}")
    monkeypatch.setenv("DIAL_CALLBACK_MAX_AGE_SECONDS", "300")
    get_settings.cache_clear()


def _seed_callback_operation() -> None:
    db = SessionLocal()
    try:
        db.add(
            OutboundCampaign(
                id="campaign-dial-sandbox-varun",
                tenant_id="varun",
                name="Day 33 Dial sandbox fixture",
                campaign_type="po_confirmation",
                status="running",
                total_targets=1,
            )
        )
        db.add(
            CampaignQueue(
                id="queue-dial-sandbox-varun",
                tenant_id="varun",
                campaign_id="campaign-dial-sandbox-varun",
                recipient_phone="+919800000033",
                recipient_name="No real provider call",
                status="dialing",
                call_id=CALL_ID,
            )
        )
        db.add(
            JobRun(
                id="job-dial-sandbox-varun",
                tenant_id="varun",
                job_type="campaign.target.dispatch",
                payload_json=json.dumps({"campaign_id": "campaign-dial-sandbox-varun", "campaign_queue_id": "queue-dial-sandbox-varun"}),
                status="retry_scheduled",
                priority=0,
                idempotency_key="dial-sandbox-idempotency-varun",
                max_attempts=3,
            )
        )
        db.add(
            ProviderOperation(
                id="provider-operation-dial-sandbox-varun",
                tenant_id="varun",
                provider="dial",
                operation_type="outbound_call",
                idempotency_key="dial-sandbox-idempotency-varun",
                provider_id=CALL_ID,
                request_hash="day33-fixture-only",
                status="accepted",
                requested_at=NOW,
                updated_at=NOW,
            )
        )
        db.commit()
    finally:
        db.close()


def _dial_event(event_id: str, event_type: str, at: datetime, data: dict) -> dict:
    return {
        "id": event_id,
        "object": "event",
        "type": event_type,
        "version": 1,
        "createdAt": at.isoformat(),
        "relatedObject": {"id": CALL_ID, "type": "call", "url": f"/api/v1/calls/{CALL_ID}"},
        "data": data,
    }


def _status_event(event_id: str, state: str, at: datetime, termination_type: str | None = None) -> dict:
    return _dial_event(
        event_id,
        "call.status_changed",
        at,
        {
            "callId": CALL_ID,
            "direction": "outbound",
            "status": {"state": state, "label": state},
            "previousState": None,
            "terminationType": termination_type,
        },
    )


def _ended_event(event_id: str, at: datetime, status: str = "completed", *, canceled: bool = False) -> dict:
    return _dial_event(
        event_id,
        "call.ended",
        at,
        {
            "callId": CALL_ID,
            "direction": "outbound",
            "durationSeconds": 47,
            "status": status,
            "canceled": canceled,
            "transcriptAvailable": False,
        },
    )


def _signed_headers(body: bytes, event: dict, *, secret: str = DIAL_SECRET_CURRENT, timestamp: int | None = None) -> dict[str, str]:
    value = str(timestamp if timestamp is not None else int(datetime.now(timezone.utc).timestamp()))
    signature = hmac.new(
        secret.encode("utf-8"),
        value.encode("ascii") + b"." + body,
        hashlib.sha256,
    ).hexdigest()
    return {
        "Content-Type": "application/json",
        "X-Dial-Event-ID": str(event["id"]),
        "X-Dial-Event-Type": str(event["type"]),
        "X-Dial-Signature": f"t={value},v1={signature}",
    }


def _post(client: TestClient, event: dict, *, secret: str = DIAL_SECRET_CURRENT, timestamp: int | None = None):
    body = json.dumps(event, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return client.post(
        "/api/provider-callbacks/dial/events",
        content=body,
        headers=_signed_headers(body, event, secret=secret, timestamp=timestamp),
    )


def test_disabled_dial_adapter_fails_closed_before_body_parsing(monkeypatch):
    monkeypatch.setenv("DIAL_CALLBACK_ADAPTER_ENABLED", "false")
    get_settings.cache_clear()
    reset_db()
    seed(reset=True)

    with TestClient(create_app()) as client:
        response = client.post("/api/provider-callbacks/dial/events", content=b"{}", headers={"Content-Type": "application/json"})

    assert response.status_code == 503
    assert response.json()["detail"] == "dial_callback_adapter_disabled"
    db = SessionLocal()
    try:
        assert db.query(ProviderEvent).count() == 0
        assert db.query(ProviderCallbackAdapterAudit).count() == 0
    finally:
        db.close()


def test_dial_sandbox_lifecycle_secret_rotation_replay_and_ordering(monkeypatch):
    _configure_adapter(monkeypatch)
    reset_db()
    seed(reset=True)
    _seed_callback_operation()
    queued = _status_event("evt-dial-queued-1", "Queued", NOW)
    connected = _status_event("evt-dial-connected-1", "In-Progress", NOW + timedelta(seconds=5))
    terminal = _ended_event("evt-dial-ended-1", NOW + timedelta(seconds=20))
    delayed = _status_event("evt-dial-delayed-1", "In-Progress", NOW + timedelta(seconds=2))

    with TestClient(create_app()) as client:
        first = _post(client, queued, secret=DIAL_SECRET_PREVIOUS)
        duplicate = _post(client, queued, secret=DIAL_SECRET_PREVIOUS)
        connected_response = _post(client, connected)
        terminal_response = _post(client, terminal)
        delayed_response = _post(client, delayed)
        analytics = client.get("/api/analytics/overview?tenant_id=varun&days=7")

    assert first.status_code == 200 and first.json()["state"] == "applied"
    assert duplicate.status_code == 200 and duplicate.json()["state"] == "duplicate"
    assert connected_response.status_code == 200 and connected_response.json()["state"] == "applied"
    assert terminal_response.status_code == 200 and terminal_response.json()["state"] == "applied"
    assert delayed_response.status_code == 200
    assert delayed_response.json()["apply_status"] == "ignored_terminal"

    db = SessionLocal()
    try:
        operation = db.get(ProviderOperation, "provider-operation-dial-sandbox-varun")
        queue = db.get(CampaignQueue, "queue-dial-sandbox-varun")
        job = db.get(JobRun, "job-dial-sandbox-varun")
        provider_events = db.query(ProviderEvent).order_by(ProviderEvent.created_at).all()
        audits = db.query(ProviderCallbackAdapterAudit).order_by(ProviderCallbackAdapterAudit.created_at).all()
        assert operation is not None and operation.status == "confirmed"
        assert queue is not None and queue.status == "completed"
        assert job is not None and job.status == "succeeded"
        assert len(provider_events) == 4  # exact replay did not create a second lifecycle event
        assert len(audits) == 4  # the adapter audit is idempotent for the exact replay too
        assert audits[-1].application_status == "ignored_terminal"
        assert all(audit.tenant_id == "varun" for audit in audits)
    finally:
        db.close()

    assert analytics.status_code == 200
    adapter = analytics.json()["dial_sandbox_adapter"]
    assert adapter["adapter_enabled"] is True
    assert adapter["sandbox_mode"] is True
    assert adapter["tenant_allowed"] is True
    assert adapter["audit_count"] == 4
    assert adapter["application_status_counts"]["applied"] == 3
    assert adapter["application_status_counts"]["ignored_terminal"] == 1


def test_tampered_signature_is_audited_and_rejected_before_normalization(monkeypatch):
    _configure_adapter(monkeypatch)
    reset_db()
    seed(reset=True)
    _seed_callback_operation()
    event = _status_event("evt-dial-invalid-1", "Queued", NOW)
    body = json.dumps(event, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sent_at = int(datetime.now(timezone.utc).timestamp())
    headers = _signed_headers(body, event, timestamp=sent_at)
    headers["X-Dial-Signature"] = f"t={sent_at},v1=bad"

    with TestClient(create_app()) as client:
        response = client.post("/api/provider-callbacks/dial/events", content=body, headers=headers)

    assert response.status_code == 403
    assert response.json()["detail"] == "invalid_dial_signature"
    db = SessionLocal()
    try:
        assert db.query(ProviderEvent).count() == 0
        audit = db.query(ProviderCallbackAdapterAudit).one()
        assert audit.verification_status == "rejected"
        assert audit.normalization_status == "not_normalized"
        assert audit.application_status == "rejected"
        assert audit.reason_code == "invalid_dial_signature"
        assert audit.tenant_id is None
    finally:
        db.close()


def test_stale_dial_callback_is_rejected_before_normalization(monkeypatch):
    _configure_adapter(monkeypatch)
    reset_db()
    seed(reset=True)
    _seed_callback_operation()
    event = _status_event("evt-dial-stale-1", "Queued", NOW)

    with TestClient(create_app()) as client:
        response = _post(client, event, timestamp=int((datetime.now(timezone.utc) - timedelta(minutes=10)).timestamp()))

    assert response.status_code == 403
    assert response.json()["detail"] == "stale_dial_signature_timestamp"
    db = SessionLocal()
    try:
        assert db.query(ProviderEvent).count() == 0
        audit = db.query(ProviderCallbackAdapterAudit).one()
        assert audit.reason_code == "stale_dial_signature_timestamp"
        assert audit.normalization_status == "not_normalized"
    finally:
        db.close()


def test_verified_dial_callback_is_blocked_without_an_explicit_tenant_allow_list(monkeypatch):
    _configure_adapter(monkeypatch, allowed_tenants="callback-other")
    reset_db()
    seed(reset=True)
    _seed_callback_operation()
    event = _status_event("evt-dial-blocked-1", "Queued", NOW)

    with TestClient(create_app()) as client:
        response = _post(client, event)

    assert response.status_code == 200
    assert response.json()["state"] == "blocked"
    assert response.json()["apply_status"] == "blocked_tenant"
    db = SessionLocal()
    try:
        assert db.query(ProviderEvent).count() == 0
        audit = db.query(ProviderCallbackAdapterAudit).one()
        assert audit.tenant_id == "varun"
        assert audit.application_status == "blocked_tenant"
        assert audit.reason_code == "dial_callback_tenant_not_allowed"
        operation = db.get(ProviderOperation, "provider-operation-dial-sandbox-varun")
        assert operation is not None and operation.status == "accepted"
    finally:
        db.close()


def test_signed_ping_is_acknowledged_without_a_provider_lifecycle_event(monkeypatch):
    _configure_adapter(monkeypatch)
    reset_db()
    seed(reset=True)
    ping = {
        "id": "evt-dial-ping-1",
        "object": "event",
        "type": "webhook.ping",
        "version": 1,
        "createdAt": NOW.isoformat(),
        "relatedObject": None,
        "data": {},
    }

    with TestClient(create_app()) as client:
        response = _post(client, ping)

    assert response.status_code == 200
    assert response.json()["state"] == "ping_acknowledged"
    db = SessionLocal()
    try:
        assert db.query(ProviderEvent).count() == 0
        audit = db.query(ProviderCallbackAdapterAudit).one()
        assert audit.verification_status == "verified"
        assert audit.normalization_status == "ping"
        assert audit.application_status == "acknowledged"
        assert audit.tenant_id is None
    finally:
        db.close()
