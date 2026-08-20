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
    ProviderCallbackAdapterAudit,
    SessionLocal,
    SideEffectIntent,
    WorksheetLog,
    Tenant,
    reset_db,
)
from voxflow_api.jobs.side_effects import NOTIFICATION_DISPATCH, SHEETS_CALL_OUTCOME, enqueue_side_effect
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


def test_day33_adapter_analytics_is_tenant_scoped_and_redacted():
    reset_db()
    seed(reset=True)
    _seed_analytics_rows()
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        db.add_all(
            [
                ProviderCallbackAdapterAudit(
                    id="adapter-audit-varun-rejected",
                    tenant_id="varun",
                    provider="dial",
                    provider_event_id="evt-varun-rejected",
                    provider_event_type="call.status_changed",
                    payload_hash="hash-varun-rejected",
                    verification_status="rejected",
                    normalization_status="not_normalized",
                    application_status="rejected",
                    reason_code="invalid_dial_signature",
                    created_at=now,
                ),
                ProviderCallbackAdapterAudit(
                    id="adapter-audit-varun-blocked",
                    tenant_id="varun",
                    provider="dial",
                    provider_event_id="evt-varun-blocked",
                    provider_event_type="call.ended",
                    payload_hash="hash-varun-blocked",
                    verification_status="verified",
                    normalization_status="normalized",
                    application_status="blocked_tenant",
                    reason_code="dial_callback_tenant_not_allowed",
                    created_at=now,
                ),
                ProviderCallbackAdapterAudit(
                    id="adapter-audit-other",
                    tenant_id="tenant-analytics-other",
                    provider="dial",
                    provider_event_id="evt-other-private",
                    provider_event_type="call.ended",
                    payload_hash="hash-other-private",
                    verification_status="verified",
                    normalization_status="normalized",
                    application_status="applied",
                    reason_code=None,
                    created_at=now,
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    with TestClient(create_app()) as client:
        response = client.get("/api/analytics/overview?tenant_id=varun&days=7")
        other = client.get("/api/analytics/overview?tenant_id=tenant-analytics-other&days=7")
        report = client.get("/api/analytics/report.csv?tenant_id=varun&days=7")

    assert response.status_code == 200
    adapter = response.json()["dial_sandbox_adapter"]
    assert adapter["audit_count"] == 2
    assert adapter["verification_failure_count"] == 1
    assert adapter["blocked_application_count"] == 1
    assert adapter["verification_status_counts"] == {"rejected": 1, "verified": 1}
    assert adapter["application_status_counts"] == {"blocked_tenant": 1, "rejected": 1}
    alert_codes = {alert["code"] for alert in response.json()["monitoring"]["alerts"]}
    assert {"dial_callback_verification_failures", "dial_callback_rollout_blocked"} <= alert_codes
    assert "evt-other-private" not in str(response.json())

    assert other.status_code == 200
    assert other.json()["dial_sandbox_adapter"]["audit_count"] == 1
    assert other.json()["dial_sandbox_adapter"]["application_status_counts"] == {"applied": 1}
    assert report.status_code == 200
    assert "Dial adapter verification failures,1" in report.text
    assert "evt-varun-rejected" not in report.text
    assert "hash-varun-rejected" not in report.text


def test_day34_side_effect_analytics_is_tenant_scoped_and_redacted():
    reset_db()
    seed(reset=True)
    _seed_analytics_rows()
    db = SessionLocal()
    try:
        worksheet = WorksheetLog(
            tenant_id="varun",
            worksheet_name="Call Log",
            action_type="append",
            row_data_json='{"phone":"+919999999999","secret":"not-in-analytics"}',
        )
        other_worksheet = WorksheetLog(
            tenant_id="tenant-analytics-other",
            worksheet_name="Call Log",
            action_type="append",
            row_data_json='{"phone":"+911111111111","secret":"other-private"}',
        )
        db.add_all([worksheet, other_worksheet])
        db.flush()
        varun = enqueue_side_effect(
            db,
            tenant_id="varun",
            effect_type=SHEETS_CALL_OUTCOME,
            aggregate_type="worksheet_log",
            aggregate_id=str(worksheet.id),
            idempotency_key="analytics-side-effect-varun",
        )
        enqueue_side_effect(
            db,
            tenant_id="tenant-analytics-other",
            effect_type=NOTIFICATION_DISPATCH,
            aggregate_type="communication_log",
            aggregate_id="private-comm-id",
            idempotency_key="analytics-side-effect-other",
        )
        intent = db.get(SideEffectIntent, varun.intent_id)
        assert intent is not None
        intent.status = "retry_scheduled"
        intent.result_code = "http_503"
        db.commit()
    finally:
        db.close()

    with TestClient(create_app()) as client:
        response = client.get("/api/analytics/overview?tenant_id=varun&days=7")
        other_response = client.get("/api/analytics/overview?tenant_id=tenant-analytics-other&days=7")
        report = client.get("/api/analytics/report.csv?tenant_id=varun&days=7")

    assert response.status_code == 200
    side_effects = response.json()["durable_side_effects"]
    assert side_effects["activation_mode"] == "staged"
    assert side_effects["dry_run"] is True
    assert side_effects["tenant_allowed"] is False
    assert side_effects["intent_count"] == 1
    assert side_effects["pending_count"] == 1
    assert side_effects["error_count"] == 1
    assert side_effects["type_counts"] == {"sheets.call_outcome.append": 1}
    assert side_effects["status_counts"] == {"retry_scheduled": 1}
    alert_codes = {alert["code"] for alert in response.json()["monitoring"]["alerts"]}
    assert {"side_effect_error_evidence", "side_effects_staged"} <= alert_codes
    assert "+919999999999" not in str(response.json())
    assert "not-in-analytics" not in str(response.json())

    assert other_response.status_code == 200
    assert other_response.json()["durable_side_effects"]["intent_count"] == 1
    assert other_response.json()["durable_side_effects"]["type_counts"] == {"notification.dispatch": 1}
    assert report.status_code == 200
    assert "Durable side-effect intents,1" in report.text
    assert "not-in-analytics" not in report.text
    assert "+919999999999" not in report.text


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
