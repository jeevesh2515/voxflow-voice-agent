"""Day 30 policy-control and audit-read API tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from voxflow_api.db import CampaignPolicyDecision, CampaignQueue, JobRun, SessionLocal, Tenant, reset_db
from voxflow_api.main import create_app
from voxflow_api.seed import seed


def test_tenant_policy_and_recipient_consent_controls_are_validated_and_scoped():
    reset_db()
    seed(reset=True)
    with TestClient(create_app()) as client:
        initial = client.get("/api/campaign-policies/varun")
        invalid_timezone = client.put(
            "/api/campaign-policies/varun",
            json={"timezone_name": "not/a-timezone", "calling_window_start": "09:00", "calling_window_end": "18:00"},
        )
        saved = client.put(
            "/api/campaign-policies/varun",
            json={
                "timezone_name": "Asia/Kolkata",
                "calling_window_start": "09:00",
                "calling_window_end": "18:00",
                "daily_call_limit": 25,
                "max_in_flight": 2,
                "enabled": True,
            },
        )
        preference = client.put(
            "/api/campaign-policies/varun/recipients/+919876543210",
            json={
                "consent_status": "withdrawn",
                "consent_purpose": "outbound_campaign",
                "opted_out": True,
                "source": "day30-route-test",
            },
        )
        read_back = client.get("/api/campaign-policies/varun/recipients/+919876543210")

    assert initial.status_code == 200
    assert initial.json() == {"tenant_id": "varun", "configured": False}
    assert invalid_timezone.status_code == 422
    assert saved.status_code == 200
    assert saved.json()["configured"] is True
    assert saved.json()["daily_call_limit"] == 25
    assert saved.json()["max_in_flight"] == 2
    assert preference.status_code == 200
    assert preference.json()["consent_status"] == "withdrawn"
    assert preference.json()["opted_out"] is True
    assert read_back.status_code == 200
    assert read_back.json()["source"] == "day30-route-test"


def test_campaign_policy_audit_is_tenant_scoped_and_redacts_evidence_payloads():
    reset_db()
    seed(reset=True)
    payload = {
        "name": "Auditable policy campaign",
        "campaign_type": "po_confirmation",
        "targets": [{"phone": "+919876543210", "name": "Policy contact", "context": {}}],
        "auto_start": True,
    }
    with TestClient(create_app()) as client:
        created = client.post("/api/campaigns?tenant_id=varun", json=payload)
        campaign_id = created.json()["id"]

    db = SessionLocal()
    try:
        queue = db.query(CampaignQueue).filter(CampaignQueue.campaign_id == campaign_id).one()
        job = db.query(JobRun).filter(JobRun.tenant_id == "varun").order_by(JobRun.created_at.desc()).first()
        assert job is not None
        db.add(Tenant(id="tenant-other", name="Other Tenant"))
        db.add(
            CampaignPolicyDecision(
                id="cpd-route-test",
                tenant_id="varun",
                job_id=job.id,
                campaign_id=campaign_id,
                campaign_queue_id=queue.id,
                decision="cancelled",
                reason_code="recipient_opted_out",
                evidence_json='{"recipient_phone":"+919876543210","private":"do-not-expose"}',
            )
        )
        db.commit()
    finally:
        db.close()

    with TestClient(create_app()) as client:
        decisions = client.get(f"/api/campaigns/{campaign_id}/policy-decisions?tenant_id=varun")
        other_tenant = client.get(f"/api/campaigns/{campaign_id}/policy-decisions?tenant_id=tenant-other")
        queue_other_tenant = client.get(f"/api/campaigns/{campaign_id}/queue?tenant_id=tenant-other")

    assert decisions.status_code == 200
    assert decisions.json()[0]["reason_code"] == "recipient_opted_out"
    assert "evidence_json" not in decisions.json()[0]
    assert "private" not in str(decisions.json()[0])
    assert other_tenant.status_code == 404
    assert queue_other_tenant.status_code == 404
