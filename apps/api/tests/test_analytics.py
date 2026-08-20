"""Day 31 tests for tenant-safe operational analytics and reporting."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from voxflow_api.db import (
    Call,
    CampaignPolicyDecision,
    CampaignQueue,
    JobOutbox,
    JobRun,
    OutboundCampaign,
    SessionLocal,
    Tenant,
    reset_db,
)
from voxflow_api.main import create_app
from voxflow_api.seed import seed


def _seed_analytics_rows() -> None:
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        # The standard seed includes one Varun call; this test owns its reporting window.
        db.query(Call).filter(Call.tenant_id == "varun").delete()
        db.add(Tenant(id="tenant-analytics-other", name="Other Analytics Tenant"))
        db.add_all(
            [
                Call(
                    id="call-analytics-resolved",
                    tenant_id="varun",
                    started_at=now - timedelta(days=1),
                    ended_at=now - timedelta(days=1) + timedelta(seconds=90),
                    duration_sec=90,
                    caller_phone="+919876543210",
                    caller_name="Analytics Contact",
                    language="hi",
                    intent="shipment_status",
                    outcome="completed",
                    resolution_status="resolved",
                    satisfaction="happy",
                    verified=1,
                    transcript_json='[{"role":"caller","text":"private transcript"}]',
                ),
                Call(
                    id="call-analytics-escalated",
                    tenant_id="varun",
                    started_at=now - timedelta(days=2),
                    duration_sec=30,
                    caller_phone="+919812345678",
                    language="en",
                    intent="order",
                    outcome="escalated",
                    escalated=1,
                    resolution_status="partial",
                    follow_up_required=1,
                ),
                Call(
                    id="call-analytics-other",
                    tenant_id="tenant-analytics-other",
                    started_at=now - timedelta(days=1),
                    duration_sec=300,
                    caller_phone="+911111111111",
                    intent="=other_tenant_formula",
                    outcome="completed",
                    resolution_status="resolved",
                ),
            ]
        )
        db.add(
            OutboundCampaign(
                id="campaign-analytics-varun",
                tenant_id="varun",
                name="Varun Analytics Campaign",
                campaign_type="po_confirmation",
                status="paused",
                total_targets=2,
            )
        )
        db.add(
            CampaignQueue(
                id="queue-analytics-varun",
                tenant_id="varun",
                campaign_id="campaign-analytics-varun",
                recipient_phone="+919800000001",
                recipient_name="No outbound call",
                status="cancelled",
            )
        )
        db.add(
            CampaignPolicyDecision(
                id="policy-analytics-varun",
                tenant_id="varun",
                job_id="job-analytics-dead",
                campaign_id="campaign-analytics-varun",
                campaign_queue_id="queue-analytics-varun",
                decision="cancelled",
                reason_code="recipient_opted_out",
                evidence_json='{"private_phone":"+919800000001"}',
                created_at=now - timedelta(hours=2),
            )
        )
        db.add_all(
            [
                JobRun(
                    id="job-analytics-dead",
                    tenant_id="varun",
                    job_type="campaign.target.dispatch",
                    payload_json='{"secret":"do-not-report"}',
                    status="dead_lettered",
                    priority=0,
                    idempotency_key="analytics-dead",
                    max_attempts=3,
                    last_error_code="permanent_provider_failure",
                ),
                JobRun(
                    id="job-analytics-expired",
                    tenant_id="varun",
                    job_type="campaign.target.dispatch",
                    payload_json='{"secret":"do-not-report"}',
                    status="running",
                    priority=0,
                    idempotency_key="analytics-expired",
                    max_attempts=3,
                    lease_expires_at=now - timedelta(minutes=1),
                ),
                JobRun(
                    id="job-analytics-other",
                    tenant_id="tenant-analytics-other",
                    job_type="campaign.target.dispatch",
                    payload_json='{"other":"secret"}',
                    status="ready",
                    priority=0,
                    idempotency_key="analytics-other",
                    max_attempts=3,
                ),
                JobOutbox(
                    id="outbox-analytics-varun",
                    tenant_id="varun",
                    event_type="campaign.target.queued",
                    aggregate_type="campaign_queue",
                    aggregate_id="queue-analytics-varun",
                    payload_json='{"recipient":"+919800000001"}',
                    idempotency_key="analytics-outbox",
                    created_at=now - timedelta(minutes=20),
                ),
            ]
        )
        db.commit()
    finally:
        db.close()


def test_analytics_overview_is_tenant_scoped_and_reports_operational_metrics():
    reset_db()
    seed(reset=True)
    _seed_analytics_rows()

    with TestClient(create_app()) as client:
        response = client.get("/api/analytics/overview?tenant_id=varun&days=7")
        other = client.get("/api/analytics/overview?tenant_id=tenant-analytics-other&days=7")

    assert response.status_code == 200
    payload = response.json()
    assert payload["tenant"]["id"] == "varun"
    assert payload["kpis"]["total_calls"] == 2
    assert payload["kpis"]["resolved_calls"] == 1
    assert payload["kpis"]["escalated_calls"] == 1
    assert payload["kpis"]["open_follow_ups"] == 1
    assert payload["distribution"]["intents"] == {"order": 1, "shipment_status": 1}
    assert payload["campaigns"]["policy_decision_counts"] == {"cancelled": 1}
    assert payload["campaigns"]["policy_reason_counts"] == {"recipient_opted_out": 1}
    assert payload["monitoring"]["state"] == "critical"
    assert payload["monitoring"]["expired_leases"] == 1
    assert payload["monitoring"]["dead_lettered_jobs"] == 1
    assert payload["monitoring"]["unpublished_outbox"] == 1
    assert payload["monitoring"]["rollout"]["activation_mode"] == "staged"
    assert payload["monitoring"]["rollout"]["canary_allowed"] is False
    assert payload["monitoring"]["rollout"]["dry_run"] is True
    assert "private transcript" not in str(payload)
    assert "+919800000001" not in str(payload)
    assert "do-not-report" not in str(payload)

    assert other.status_code == 200
    assert other.json()["kpis"]["total_calls"] == 1
    assert other.json()["monitoring"]["dead_lettered_jobs"] == 0


def test_analytics_csv_report_is_tenant_safe_and_excludes_sensitive_payloads():
    reset_db()
    seed(reset=True)
    _seed_analytics_rows()

    with TestClient(create_app()) as client:
        response = client.get("/api/analytics/report.csv?tenant_id=varun&days=7")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "voxflow-varun-operations-report" in response.headers["content-disposition"]
    body = response.text
    assert "VoxFlow Enterprise Operations Report" in body
    assert "total_calls,2" in body
    assert "private transcript" not in body
    assert "+919876543210" not in body
    assert "+919800000001" not in body
    assert "do-not-report" not in body
    assert "private_phone" not in body
