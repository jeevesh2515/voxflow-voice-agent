"""Day 36 evidence-led controlled-pilot operations tests.

Every test remains database-only. No worker, provider adapter, callback secret,
notification, CRM, email, recording, or supplier contact is enabled.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from voxflow_api.config import get_settings
from voxflow_api.db import (
    JobRun,
    PilotCohortMember,
    PilotConfiguration,
    PilotOperationalEvidence,
    SessionLocal,
    reset_db,
)
from voxflow_api.main import create_app
from voxflow_api.pilot_operations import (
    hold_point_scorecard,
    operational_preflight,
    record_operational_evidence,
)
from voxflow_api.pilot_readiness import evaluate_pilot_admission, hash_recipient
from voxflow_api.seed import seed


NOW = datetime(2026, 8, 21, 8, 0, tzinfo=timezone.utc)
PHONE = "+919876543210"


@pytest.fixture(autouse=True)
def fresh_database():
    reset_db()
    seed(reset=True)


@pytest.fixture
def production_pilot_operations_gate(monkeypatch):
    monkeypatch.setenv("PILOT_READINESS_ENFORCED", "true")
    monkeypatch.setenv("PILOT_READINESS_APPROVED_TENANTS", "varun")
    monkeypatch.setenv("PILOT_OPERATIONS_EVIDENCE_ENFORCED", "true")
    monkeypatch.setenv("DURABLE_CAMPAIGN_WORKER_ENABLED", "false")
    monkeypatch.setenv("DURABLE_CAMPAIGN_DRY_RUN", "true")
    monkeypatch.setenv("DURABLE_SIDE_EFFECTS_WORKER_ENABLED", "false")
    monkeypatch.setenv("DURABLE_SIDE_EFFECTS_DRY_RUN", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _add_config_and_member(db):
    config = PilotConfiguration(
        tenant_id="varun",
        pilot_id="pilot-varun-day36",
        version=1,
        status="approved",
        cohort_id="cohort-varun-day36",
        cohort_size=1,
        timezone_name="Asia/Kolkata",
        calling_window_start="09:00",
        calling_window_end="20:00",
        daily_call_limit=1,
        max_in_flight=1,
        expires_at=NOW + timedelta(days=1),
        primary_escalation_owner="Primary Owner",
        backup_escalation_owner="Backup Owner",
        metric_contract_version="day35-v1",
        approved_by="Pilot Approver",
        approved_at=NOW - timedelta(minutes=5),
    )
    member = PilotCohortMember(
        id="pcm-day36-varun",
        tenant_id="varun",
        cohort_id=config.cohort_id,
        recipient_hash=hash_recipient(PHONE),
        consent_evidence_ref="consent-redacted-day36",
        status="approved",
        reviewed_at=NOW - timedelta(minutes=5),
    )
    db.add_all([config, member])
    db.commit()
    return config


def test_preflight_is_blocked_without_configuration_and_never_creates_work():
    db = SessionLocal()
    try:
        payload = operational_preflight(db, tenant_id="varun", now=NOW)
        created = db.query(JobRun).filter(JobRun.tenant_id == "varun").count()
    finally:
        db.close()
    assert payload["configured"] is False
    assert payload["preflight"]["state"] == "blocked"
    assert payload["preflight"]["no_auto_expansion"] is True
    assert payload["preflight"]["requires_human_hold_point"] is True
    assert created == 0


def test_same_day_preflight_evidence_is_required_before_day35_admission(production_pilot_operations_gate):
    db = SessionLocal()
    try:
        _add_config_and_member(db)
        blocked = evaluate_pilot_admission(db, tenant_id="varun", recipient_phone=PHONE, now=NOW)
        recorded = record_operational_evidence(
            db,
            tenant_id="varun",
            evidence_kind="preflight",
            evidence_key="opening-window-2026-08-21",
            decision="continue_same_cohort",
            reason_code="human_preflight_reviewed",
            recorded_by="pilot-owner",
            now=NOW,
        )
        db.commit()
        reviewed = hold_point_scorecard(db, tenant_id="varun", now=NOW)
        allowed = evaluate_pilot_admission(db, tenant_id="varun", recipient_phone=PHONE, now=NOW)
    finally:
        db.close()
    assert blocked.decision == "cancelled"
    assert blocked.reason_code == "pilot_hold_point_evidence_missing"
    assert recorded["created"] is True
    assert reviewed["hold_point"]["state"] == "reviewed_same_cohort"
    assert reviewed["hold_point"]["expansion_permitted"] is False
    assert allowed.decision == "allowed"


def test_pause_evidence_is_an_immediate_fail_closed_hold_point(production_pilot_operations_gate):
    db = SessionLocal()
    try:
        _add_config_and_member(db)
        record_operational_evidence(
            db,
            tenant_id="varun",
            evidence_kind="preflight",
            evidence_key="opening-window-2026-08-21",
            decision="continue_same_cohort",
            reason_code="human_preflight_reviewed",
            recorded_by="pilot-owner",
            now=NOW,
        )
        record_operational_evidence(
            db,
            tenant_id="varun",
            evidence_kind="pause",
            evidence_key="pause-callback-review-2026-08-21",
            decision="pause",
            reason_code="callback_review_required",
            recorded_by="primary-responder",
            now=NOW + timedelta(minutes=1),
        )
        db.commit()
        admission = evaluate_pilot_admission(db, tenant_id="varun", recipient_phone=PHONE, now=NOW + timedelta(minutes=1))
        hold = hold_point_scorecard(db, tenant_id="varun", now=NOW + timedelta(minutes=1))
    finally:
        db.close()
    assert admission.decision == "cancelled"
    assert admission.reason_code == "pilot_hold_point_pause"
    assert hold["hold_point"]["state"] == "blocked"
    assert hold["hold_point"]["expansion_permitted"] is False


def test_evidence_is_idempotent_and_snapshot_is_redacted(production_pilot_operations_gate):
    db = SessionLocal()
    try:
        _add_config_and_member(db)
        first = record_operational_evidence(
            db,
            tenant_id="varun",
            evidence_kind="preflight",
            evidence_key="opening-window-2026-08-21",
            decision="continue_same_cohort",
            reason_code="human_preflight_reviewed",
            recorded_by="pilot-owner",
            now=NOW,
        )
        second = record_operational_evidence(
            db,
            tenant_id="varun",
            evidence_kind="preflight",
            evidence_key="opening-window-2026-08-21",
            decision="continue_same_cohort",
            reason_code="human_preflight_reviewed",
            recorded_by="pilot-owner",
            now=NOW,
        )
        db.commit()
        evidence_rows = (
            db.query(PilotOperationalEvidence)
            .filter(PilotOperationalEvidence.tenant_id == "varun")
            .all()
        )
    finally:
        db.close()
    assert first["created"] is True
    assert second["created"] is False
    assert len(evidence_rows) == 1
    assert PHONE not in evidence_rows[0].snapshot_json


def test_preflight_flags_expired_campaign_lease_without_external_execution(production_pilot_operations_gate):
    db = SessionLocal()
    try:
        _add_config_and_member(db)
        db.add(
            JobRun(
                id="job-day36-expired-lease",
                tenant_id="varun",
                job_type="campaign.target.dispatch",
                payload_json="{}",
                status="running",
                idempotency_key="day36-expired-lease",
                scheduled_at=NOW,
                next_run_at=NOW,
                lease_owner="fixture-worker",
                lease_expires_at=NOW - timedelta(seconds=1),
            )
        )
        db.commit()
        preflight = operational_preflight(db, tenant_id="varun", now=NOW)
    finally:
        db.close()
    assert preflight["queue"]["campaign_expired_leases"] == 1
    assert "campaign_queue_claim_requires_manual_review" in preflight["preflight"]["blocking_reasons"]
    assert preflight["preflight"]["no_auto_expansion"] is True


def test_read_only_day36_routes_are_tenant_safe_and_reject_post():
    with TestClient(create_app()) as client:
        preflight = client.get("/api/pilot-operations/varun/preflight")
        hold = client.get("/api/pilot-operations/varun/hold-point")
        post = client.post("/api/pilot-operations/varun/preflight")
        missing = client.get("/api/pilot-operations/not-a-tenant/preflight")
    assert preflight.status_code == 200
    assert preflight.json()["preflight"]["no_auto_expansion"] is True
    assert hold.status_code == 200
    assert hold.json()["hold_point"]["expansion_permitted"] is False
    assert post.status_code == 405
    assert missing.status_code == 404


def test_other_tenant_never_sees_varun_pilot_evidence(production_pilot_operations_gate):
    db = SessionLocal()
    try:
        _add_config_and_member(db)
        record_operational_evidence(
            db,
            tenant_id="varun",
            evidence_kind="preflight",
            evidence_key="opening-window-2026-08-21",
            decision="continue_same_cohort",
            reason_code="human_preflight_reviewed",
            recorded_by="pilot-owner",
            now=NOW,
        )
        db.commit()
        other = operational_preflight(db, tenant_id="amul", now=NOW)
    finally:
        db.close()
    assert other["configured"] is False
    assert other["latest_evidence"] is None
