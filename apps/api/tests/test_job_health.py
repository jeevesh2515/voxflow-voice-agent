"""Day 28 tests for tenant-safe job-health API and safe campaign staging."""

from __future__ import annotations

from fastapi.testclient import TestClient

from voxflow_api.db import JobOutbox, JobRun, SessionLocal, Tenant, reset_db
from voxflow_api.main import create_app
from voxflow_api.seed import seed


def _seed_health_rows() -> None:
    db = SessionLocal()
    try:
        db.add(Tenant(id="tenant-other", name="Other Tenant"))
        db.add(
            JobRun(
                id="job-varun-health",
                tenant_id="varun",
                job_type="campaign.target.dispatch",
                payload_json='{"campaign_id":"cmp-varun","secret":"do-not-expose"}',
                status="ready",
                priority=0,
                idempotency_key="health-varun",
                max_attempts=3,
            )
        )
        db.add(
            JobOutbox(
                id="out-varun-health",
                tenant_id="varun",
                event_type="campaign.target.queued",
                aggregate_type="campaign_queue",
                aggregate_id="cq-varun",
                payload_json='{"recipient":"+919999999999"}',
                idempotency_key="outbox-health-varun",
            )
        )
        db.add(
            JobRun(
                id="job-other-health",
                tenant_id="tenant-other",
                job_type="notification.send",
                payload_json='{"private":"other-tenant"}',
                status="dead_lettered",
                priority=0,
                idempotency_key="health-other",
                max_attempts=1,
            )
        )
        db.commit()
    finally:
        db.close()


def test_job_health_is_tenant_scoped_and_recent_jobs_redact_payloads():
    reset_db()
    seed(reset=True)
    _seed_health_rows()
    with TestClient(create_app()) as client:
        varun = client.get("/api/jobs/health?tenant_id=varun")
        other = client.get("/api/jobs/health?tenant_id=tenant-other")
        recent = client.get("/api/jobs?tenant_id=varun&limit=10")

    assert varun.status_code == 200
    assert varun.json()["activation_mode"] == "staged"
    assert varun.json()["status_counts"]["ready"] == 1
    assert varun.json()["status_counts"]["dead_lettered"] == 0
    assert varun.json()["outbox"]["unpublished"] == 1

    assert other.status_code == 200
    assert other.json()["status_counts"]["dead_lettered"] == 1
    assert other.json()["status_counts"]["ready"] == 0
    assert other.json()["outbox"]["unpublished"] == 0

    assert recent.status_code == 200
    assert [job["id"] for job in recent.json()] == ["job-varun-health"]
    assert "payload_json" not in recent.json()[0]
    assert "secret" not in str(recent.json()[0])


def test_campaign_autostart_and_run_are_safely_staged_without_inline_telephony():
    reset_db()
    seed(reset=True)
    payload = {
        "name": "Safe staging campaign",
        "campaign_type": "po_confirmation",
        "targets": [{"phone": "+919876543210", "name": "Staged contact", "context": {}}],
        "auto_start": True,
    }
    with TestClient(create_app()) as client:
        created = client.post("/api/campaigns?tenant_id=varun", json=payload)
        campaign_id = created.json()["id"]
        staged = client.post(f"/api/campaigns/{campaign_id}/run?tenant_id=varun")
        detail = client.get(f"/api/campaigns/{campaign_id}")

    assert created.status_code == 200
    assert created.json()["execution_mode"] == "staged"
    assert staged.status_code == 200
    assert staged.json()["processed"] == 0
    assert staged.json()["execution_mode"] == "staged"
    assert detail.status_code == 200
    assert detail.json()["successful_calls"] == 0
    assert detail.json()["queue_stats"]["queued"] == 1
