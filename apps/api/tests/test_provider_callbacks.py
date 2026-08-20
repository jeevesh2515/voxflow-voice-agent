"""Day 32 tests for signed provider callback lifecycle reconciliation."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
import pytest

from voxflow_api.config import get_settings
from voxflow_api.db import (
    CampaignQueue,
    JobRun,
    OutboundCampaign,
    ProviderCallbackQuarantine,
    ProviderEvent,
    ProviderOperation,
    SessionLocal,
    Tenant,
    reset_db,
)
from voxflow_api.main import create_app
from voxflow_api.seed import seed


CALLBACK_SECRET = "day32-test-callback-secret"
NOW = datetime.now(timezone.utc).replace(microsecond=0)


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _configure_callback_secret(monkeypatch) -> None:
    monkeypatch.setenv("PROVIDER_CALLBACK_SHARED_SECRET", CALLBACK_SECRET)
    monkeypatch.setenv("PROVIDER_CALLBACK_VALIDATE_SIGNATURE", "true")
    monkeypatch.setenv("PROVIDER_CALLBACK_MAX_AGE_SECONDS", "300")
    get_settings.cache_clear()


def _signed_headers(body: bytes, timestamp: int | None = None) -> dict[str, str]:
    value = str(timestamp if timestamp is not None else int(datetime.now(timezone.utc).timestamp()))
    signature = hmac.new(
        CALLBACK_SECRET.encode("utf-8"),
        value.encode("ascii") + b"." + body,
        hashlib.sha256,
    ).hexdigest()
    return {
        "Content-Type": "application/json",
        "X-VoxFlow-Timestamp": value,
        "X-VoxFlow-Signature": signature,
    }


def _post_callback(client: TestClient, payload: dict, timestamp: int | None = None):
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return client.post("/api/provider-callbacks/events", content=body, headers=_signed_headers(body, timestamp))


def _seed_callback_operation() -> None:
    db = SessionLocal()
    try:
        db.add(Tenant(id="callback-other", name="Other Callback Tenant"))
        db.add(
            OutboundCampaign(
                id="campaign-callback-varun",
                tenant_id="varun",
                name="Callback Lifecycle Test",
                campaign_type="po_confirmation",
                status="running",
                total_targets=1,
            )
        )
        db.add(
            CampaignQueue(
                id="queue-callback-varun",
                tenant_id="varun",
                campaign_id="campaign-callback-varun",
                recipient_phone="+919800000001",
                recipient_name="No external call test",
                status="dialing",
                call_id="dial-call-varun-001",
            )
        )
        db.add(
            JobRun(
                id="job-callback-varun",
                tenant_id="varun",
                job_type="campaign.target.dispatch",
                payload_json='{"campaign_id":"campaign-callback-varun","campaign_queue_id":"queue-callback-varun"}',
                status="retry_scheduled",
                priority=0,
                idempotency_key="callback-idempotency-varun",
                max_attempts=3,
            )
        )
        db.add(
            ProviderOperation(
                id="provider-operation-callback-varun",
                tenant_id="varun",
                provider="dial",
                operation_type="outbound_call",
                idempotency_key="callback-idempotency-varun",
                provider_id="dial-call-varun-001",
                request_hash="test-hash",
                status="accepted",
                requested_at=NOW,
                updated_at=NOW,
            )
        )
        db.commit()
    finally:
        db.close()


def _event(event_id: str, event_type: str, occurred_at: datetime, outcome: str | None = None) -> dict:
    return {
        "provider": "dial",
        "event_id": event_id,
        "call_id": "dial-call-varun-001",
        "event_type": event_type,
        "occurred_at": occurred_at.isoformat(),
        "outcome": outcome,
    }


def test_callback_fails_closed_before_payload_validation_when_secret_is_not_configured(monkeypatch):
    monkeypatch.delenv("PROVIDER_CALLBACK_SHARED_SECRET", raising=False)
    monkeypatch.setenv("PROVIDER_CALLBACK_VALIDATE_SIGNATURE", "true")
    reset_db()
    seed(reset=True)
    _seed_callback_operation()

    with TestClient(create_app()) as client:
        response = client.post(
            "/api/provider-callbacks/events",
            content=b"{}",
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "provider_callback_not_configured"
    db = SessionLocal()
    try:
        assert db.query(ProviderEvent).count() == 0
    finally:
        db.close()


def test_signed_callback_lifecycle_is_idempotent_tenant_derived_and_terminal(monkeypatch):
    _configure_callback_secret(monkeypatch)
    reset_db()
    seed(reset=True)
    _seed_callback_operation()

    accepted = _event("event-accepted-1", "request_accepted", NOW)
    connected = _event("event-connected-1", "connected", NOW + timedelta(seconds=10))
    terminal = _event("event-ended-1", "ended", NOW + timedelta(seconds=20), "completed")
    late = _event("event-late-connected", "connected", NOW + timedelta(seconds=5))
    # The API ignores callback tenant input; it must derive varun from the existing operation.
    accepted["tenant_id"] = "callback-other"

    with TestClient(create_app()) as client:
        first = _post_callback(client, accepted)
        duplicate = _post_callback(client, accepted)
        connected_response = _post_callback(client, connected)
        terminal_response = _post_callback(client, terminal)
        late_response = _post_callback(client, late)
        analytics = client.get("/api/analytics/overview?tenant_id=varun&days=7")

    assert first.status_code == 200
    assert first.json()["state"] == "applied"
    assert duplicate.status_code == 200
    assert duplicate.json()["state"] == "duplicate"
    assert connected_response.json()["state"] == "applied"
    assert terminal_response.json()["state"] == "applied"
    assert late_response.json()["apply_status"] == "ignored_terminal"

    db = SessionLocal()
    try:
        operation = db.get(ProviderOperation, "provider-operation-callback-varun")
        job = db.get(JobRun, "job-callback-varun")
        queue = db.get(CampaignQueue, "queue-callback-varun")
        campaign = db.get(OutboundCampaign, "campaign-callback-varun")
        events = db.query(ProviderEvent).order_by(ProviderEvent.created_at).all()
        assert operation is not None and operation.status == "confirmed"
        assert job is not None and job.status == "succeeded"
        assert queue is not None and queue.status == "completed"
        assert campaign is not None and campaign.successful_calls == 1
        assert len(events) == 4  # exact duplicate did not create another event
        assert {event.tenant_id for event in events} == {"varun"}
        assert events[-1].apply_status == "ignored_terminal"
        assert events[-1].anomaly_code == "terminal_operation"
    finally:
        db.close()

    assert analytics.status_code == 200
    lifecycle = analytics.json()["provider_lifecycle"]
    assert lifecycle["event_count"] == 4
    assert lifecycle["anomaly_count"] == 1
    assert lifecycle["event_type_counts"]["ended"] == 1
    assert any(alert["code"] == "provider_callback_anomalies" for alert in analytics.json()["monitoring"]["alerts"])


def test_callback_rejects_invalid_or_stale_signatures_before_any_mutation(monkeypatch):
    _configure_callback_secret(monkeypatch)
    reset_db()
    seed(reset=True)
    _seed_callback_operation()
    payload = _event("event-invalid-1", "connected", NOW)
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")

    with TestClient(create_app()) as client:
        invalid = client.post(
            "/api/provider-callbacks/events",
            content=body,
            headers={"Content-Type": "application/json", "X-VoxFlow-Timestamp": str(int(datetime.now(timezone.utc).timestamp())), "X-VoxFlow-Signature": "bad"},
        )
        stale = _post_callback(client, payload, int((datetime.now(timezone.utc) - timedelta(minutes=10)).timestamp()))

    assert invalid.status_code == 403
    assert invalid.json()["detail"] == "invalid_callback_signature"
    assert stale.status_code == 403
    assert stale.json()["detail"] == "stale_callback_timestamp"

    db = SessionLocal()
    try:
        assert db.query(ProviderEvent).count() == 0
        operation = db.get(ProviderOperation, "provider-operation-callback-varun")
        assert operation is not None and operation.status == "accepted"
    finally:
        db.close()


def test_signed_unknown_callback_is_quarantined_without_tenant_inference(monkeypatch):
    _configure_callback_secret(monkeypatch)
    reset_db()
    seed(reset=True)
    _seed_callback_operation()
    unknown = {
        "provider": "dial",
        "event_id": "event-unknown-1",
        "call_id": "dial-call-unknown",
        "event_type": "ended",
        "occurred_at": NOW.isoformat(),
        "outcome": "completed",
        "tenant_id": "varun",
    }

    with TestClient(create_app()) as client:
        response = _post_callback(client, unknown)
        duplicate = _post_callback(client, unknown)

    assert response.status_code == 200
    assert response.json()["state"] == "quarantined"
    assert response.json()["anomaly_code"] == "unknown_provider_operation"
    assert duplicate.status_code == 200
    assert duplicate.json()["state"] == "duplicate"

    db = SessionLocal()
    try:
        assert db.query(ProviderEvent).count() == 0
        quarantined = db.query(ProviderCallbackQuarantine).all()
        assert len(quarantined) == 1
        assert quarantined[0].provider_call_id == "dial-call-unknown"
    finally:
        db.close()
