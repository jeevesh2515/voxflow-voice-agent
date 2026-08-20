"""Day 35 controlled-pilot readiness tests; all execution remains offline."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from voxflow_api.config import get_settings
from voxflow_api.db import (
    CampaignQueue,
    JobRun,
    OutboundCampaign,
    PilotCohortMember,
    PilotConfiguration,
    SessionLocal,
    reset_db,
)
from voxflow_api.main import create_app
from voxflow_api.pilot_readiness import (
    evaluate_pilot_admission,
    execute_database_only_rollback,
    hash_recipient,
    pilot_scorecard,
    rollback_preview,
)
from voxflow_api.seed import seed

NOW = datetime(2026, 8, 20, 10, 0, tzinfo=timezone.utc)
PHONE = "+919876540001"


@pytest.fixture(autouse=True)
def fresh_database():
    reset_db()
    seed(reset=True)


@pytest.fixture
def production_pilot_gate(monkeypatch):
    monkeypatch.setenv("PILOT_READINESS_ENFORCED", "true")
    monkeypatch.setenv("PILOT_READINESS_APPROVED_TENANTS", "varun")
    get_settings.cache_clear()
    try:
        yield
    finally:
        monkeypatch.setenv("PILOT_READINESS_ENFORCED", "false")
        monkeypatch.delenv("PILOT_READINESS_APPROVED_TENANTS", raising=False)
        get_settings.cache_clear()


def _config(*, status: str = "approved", expires_at: datetime | None = None, cohort_size: int = 1) -> PilotConfiguration:
    return PilotConfiguration(
        tenant_id="varun",
        pilot_id="pilot-varun-day35",
        version=1,
        status=status,
        cohort_id="cohort-varun-001",
        cohort_size=cohort_size,
        timezone_name="Asia/Kolkata",
        calling_window_start="09:00",
        calling_window_end="18:00",
        daily_call_limit=1,
        max_in_flight=1,
        expires_at=expires_at or NOW + timedelta(days=7),
        primary_escalation_owner="Primary Operations Lead",
        backup_escalation_owner="Backup Operations Lead",
        acknowledgement_timeout_minutes=15,
        metric_contract_version="day35-v1",
        approved_by="Tenant Pilot Owner",
        approved_at=NOW,
    )


def _add_config_and_member(db, *, status: str = "approved", expires_at: datetime | None = None, cohort_size: int = 1, phone: str = PHONE):
    config = _config(status=status, expires_at=expires_at, cohort_size=cohort_size)
    db.add(config)
    db.add(
        PilotCohortMember(
            id="pcm-varun-001",
            tenant_id="varun",
            cohort_id=config.cohort_id,
            recipient_hash=hash_recipient(phone),
            consent_evidence_ref="consent-review-001",
            status="approved",
            reviewed_at=NOW,
        )
    )
    db.commit()
    return config


def test_production_default_gate_denies_tenant_without_environment_approval(monkeypatch):
    monkeypatch.setenv("PILOT_READINESS_ENFORCED", "true")
    monkeypatch.setenv("PILOT_READINESS_APPROVED_TENANTS", "")
    get_settings.cache_clear()
    db = SessionLocal()
    try:
        result = evaluate_pilot_admission(db, tenant_id="varun", recipient_phone=PHONE, now=NOW)
    finally:
        db.close()
        monkeypatch.setenv("PILOT_READINESS_ENFORCED", "false")
        get_settings.cache_clear()
    assert result.decision == "cancelled"
    assert result.reason_code == "pilot_tenant_not_approved"


def test_pilot_gate_denies_approved_tenant_when_no_written_configuration_exists(production_pilot_gate):
    db = SessionLocal()
    try:
        result = evaluate_pilot_admission(db, tenant_id="varun", recipient_phone=PHONE, now=NOW)
    finally:
        db.close()
    assert result.decision == "cancelled"
    assert result.reason_code == "pilot_configuration_missing"


def test_pilot_gate_requires_fixed_reviewed_cohort(production_pilot_gate):
    db = SessionLocal()
    try:
        _add_config_and_member(db, cohort_size=2)
        result = evaluate_pilot_admission(db, tenant_id="varun", recipient_phone=PHONE, now=NOW)
    finally:
        db.close()
    assert result.decision == "cancelled"
    assert result.reason_code == "pilot_cohort_review_incomplete"


def test_pilot_gate_rejects_non_cohort_recipient_even_after_approval(production_pilot_gate):
    db = SessionLocal()
    try:
        _add_config_and_member(db)
        result = evaluate_pilot_admission(db, tenant_id="varun", recipient_phone="+919876549999", now=NOW)
    finally:
        db.close()
    assert result.decision == "cancelled"
    assert result.reason_code == "pilot_cohort_mismatch"


def test_pilot_gate_rejects_expired_pilot_before_dispatch(production_pilot_gate):
    db = SessionLocal()
    try:
        _add_config_and_member(db, expires_at=NOW - timedelta(seconds=1))
        result = evaluate_pilot_admission(db, tenant_id="varun", recipient_phone=PHONE, now=NOW)
    finally:
        db.close()
    assert result.decision == "cancelled"
    assert result.reason_code == "pilot_expired"


def test_pilot_gate_admits_only_complete_approved_micro_cohort(production_pilot_gate):
    db = SessionLocal()
    try:
        _add_config_and_member(db)
        result = evaluate_pilot_admission(db, tenant_id="varun", recipient_phone=PHONE, now=NOW)
    finally:
        db.close()
    assert result.decision == "allowed"
    assert result.reason_code == "pilot_admission_allowed"
    assert result.evidence["pilot_id"] == "pilot-varun-day35"


def test_scorecard_reports_blocked_state_and_frozen_metric_contract_without_configuration():
    db = SessionLocal()
    try:
        scorecard = pilot_scorecard(db, tenant_id="varun", now=NOW)
    finally:
        db.close()
    assert scorecard["configured"] is False
    assert scorecard["readiness"]["state"] == "blocked"
    assert scorecard["readiness"]["blocking_reasons"] == ["pilot_configuration_missing"]
    assert set(scorecard["metric_contract"]) == {
        "successful_call_completion",
        "escalation_rate",
        "first_call_resolution",
        "security_incidents",
    }


def test_scorecard_keeps_workers_disabled_and_reports_zero_observed_metrics(production_pilot_gate):
    db = SessionLocal()
    try:
        _add_config_and_member(db)
        scorecard = pilot_scorecard(db, tenant_id="varun", now=NOW)
    finally:
        db.close()
    assert scorecard["readiness"]["state"] == "ready_for_review"
    assert scorecard["readiness"]["workers"]["campaign_worker_enabled"] is False
    assert scorecard["readiness"]["workers"]["side_effect_worker_enabled"] is False
    assert scorecard["metrics"]["successful_call_completion"]["rate"] is None
    assert scorecard["metrics"]["security_incidents"]["confirmed_count"] == 0


def test_database_only_rollback_cancels_only_unclaimed_pilot_jobs_and_never_calls_a_provider(production_pilot_gate):
    db = SessionLocal()
    try:
        config = _add_config_and_member(db)
        campaign = OutboundCampaign(
            id="cmp-pilot-001",
            tenant_id="varun",
            name="Day 35 Pilot Fixture",
            campaign_type="po_confirmation",
            status="active",
            total_targets=1,
        )
        target = CampaignQueue(
            id="cq-pilot-001",
            campaign_id=campaign.id,
            tenant_id="varun",
            recipient_phone=PHONE,
            recipient_name="Redacted Fixture",
            status="queued",
        )
        job = JobRun(
            id="job-pilot-001",
            tenant_id="varun",
            job_type="campaign.target.dispatch",
            payload_json=json.dumps({"campaign_id": campaign.id, "campaign_queue_id": target.id}),
            status="ready",
            idempotency_key="pilot-job-001",
            scheduled_at=NOW,
            next_run_at=NOW,
        )
        db.add_all([campaign, target, job])
        db.commit()

        preview = rollback_preview(db, tenant_id="varun")
        result = execute_database_only_rollback(db, tenant_id="varun", confirmed_by="Pilot Owner", now=NOW)
        db.commit()
        db.refresh(job)
        db.refresh(target)
        db.refresh(config)
    finally:
        db.close()
    assert preview["can_execute"] is True
    assert preview["would_cancel_job_count"] == 1
    assert result["cancelled_job_count"] == 1
    assert result["external_calls"] == 0
    assert job.status == "cancelled"
    assert job.last_error_code == "pilot_rollback"
    assert target.status == "cancelled"
    assert config.status == "rolled_back"


def test_read_only_api_returns_tenant_safe_blocked_scorecard_and_has_no_post_route():
    with TestClient(create_app()) as client:
        response = client.get("/api/pilot-readiness/varun")
        preview = client.get("/api/pilot-readiness/varun/rollback-preview")
        post = client.post("/api/pilot-readiness/varun")
    assert response.status_code == 200
    assert response.json()["readiness"]["state"] == "blocked"
    assert preview.status_code == 200
    assert preview.json()["can_execute"] is False
    assert post.status_code == 405


def test_tenant_isolation_never_admits_a_different_tenant_from_varun_cohort(production_pilot_gate):
    db = SessionLocal()
    try:
        _add_config_and_member(db)
        result = evaluate_pilot_admission(db, tenant_id="amul", recipient_phone=PHONE, now=NOW)
    finally:
        db.close()
    assert result.decision == "cancelled"
    assert result.reason_code == "pilot_tenant_not_approved"
