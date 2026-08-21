"""Day 37 reliability SLO, deterministic drill, and recovery-preview tests.

All fixtures are local database observations.  No test starts a worker, opens a
network connection, calls a provider, creates a campaign target, or contacts a
recipient.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from voxflow_api.config import get_settings
from voxflow_api.db import DrillResult, JobRun, ProviderOperation, ReliabilitySLO, SessionLocal, reset_db
from voxflow_api.main import create_app
from voxflow_api.reliability import (
    DRILL_FIXTURES,
    list_drill_results,
    recovery_plan_preview,
    reliability_scorecard,
    run_deterministic_drill,
)
from voxflow_api.seed import seed


NOW = datetime(2026, 8, 21, 8, 0, tzinfo=timezone.utc)
PHONE = "+919876543210"


@pytest.fixture(autouse=True)
def fresh_database_and_safe_posture(monkeypatch):
    monkeypatch.setenv("DURABLE_CAMPAIGN_WORKER_ENABLED", "false")
    monkeypatch.setenv("DURABLE_CAMPAIGN_DRY_RUN", "true")
    monkeypatch.setenv("DURABLE_SIDE_EFFECTS_WORKER_ENABLED", "false")
    monkeypatch.setenv("DURABLE_SIDE_EFFECTS_DRY_RUN", "true")
    get_settings.cache_clear()
    reset_db()
    seed(reset=True)
    yield
    get_settings.cache_clear()


def _expired_campaign_job() -> JobRun:
    return JobRun(
        id="job-day37-expired-lease",
        tenant_id="varun",
        job_type="campaign.target.dispatch",
        payload_json="{}",
        status="running",
        idempotency_key="day37-expired-lease",
        scheduled_at=NOW,
        next_run_at=NOW,
        lease_owner="fixture-worker",
        lease_expires_at=NOW - timedelta(seconds=1),
    )


def test_scorecard_uses_tenant_safe_default_contract_and_preserves_safe_posture():
    db = SessionLocal()
    try:
        scorecard = reliability_scorecard(db, tenant_id="varun", now=NOW)
    finally:
        db.close()
    assert scorecard["tenant_id"] == "varun"
    assert scorecard["read_only"] is True
    assert {item["metric_type"] for item in scorecard["slos"]} == {
        "queue_recovery",
        "callback_integrity",
        "evidence_freshness",
        "safety_posture",
        "drill_pass_rate",
    }
    assert scorecard["safety_guardrails"]["safe"] is True
    assert scorecard["safety_guardrails"]["external_actions"] == 0
    assert scorecard["safety_guardrails"]["worker_activation_available"] is False


def test_expired_lease_fails_only_the_queue_recovery_measurement_without_mutation():
    db = SessionLocal()
    try:
        db.add(_expired_campaign_job())
        db.commit()
        before_count = db.query(JobRun).filter(JobRun.tenant_id == "varun").count()
        scorecard = reliability_scorecard(db, tenant_id="varun", now=NOW)
        after_count = db.query(JobRun).filter(JobRun.tenant_id == "varun").count()
    finally:
        db.close()
    queue_slo = next(item for item in scorecard["slos"] if item["metric_type"] == "queue_recovery")
    assert queue_slo["actual_percent"] == 0.0
    assert queue_slo["status"] == "failing"
    assert queue_slo["evidence"]["campaign_expired_leases"] == 1
    assert before_count == after_count == 1


def test_stored_slo_definition_overrides_only_its_tenant_contract():
    db = SessionLocal()
    try:
        db.add(
            ReliabilitySLO(
                id="slo-varun-queue",
                tenant_id="varun",
                metric_type="queue_recovery",
                target_percent=99.5,
                window_hours=12,
                comparison="minimum",
                active=1,
            )
        )
        db.commit()
        varun = reliability_scorecard(db, tenant_id="varun", now=NOW)
        amul = reliability_scorecard(db, tenant_id="amul", now=NOW)
    finally:
        db.close()
    varun_queue = next(item for item in varun["slos"] if item["metric_type"] == "queue_recovery")
    amul_queue = next(item for item in amul["slos"] if item["metric_type"] == "queue_recovery")
    assert varun_queue["target_percent"] == 99.5
    assert varun_queue["window_hours"] == 12
    assert varun_queue["source"] == "tenant_configuration"
    assert amul_queue["target_percent"] == 100.0
    assert amul_queue["source"] == "built_in_contract"


@pytest.mark.parametrize("fixture_type", sorted(DRILL_FIXTURES))
def test_every_deterministic_fault_fixture_records_only_a_safe_database_receipt(fixture_type: str):
    db = SessionLocal()
    try:
        before_jobs = db.query(JobRun).count()
        before_provider_operations = db.query(ProviderOperation).count()
        result = run_deterministic_drill(
            db,
            tenant_id="varun",
            fixture_type=fixture_type,
            execution_key=f"day37-{fixture_type}",
            now=NOW,
        )
        db.commit()
        receipt = db.get(DrillResult, result["id"])
        after_jobs = db.query(JobRun).count()
        after_provider_operations = db.query(ProviderOperation).count()
    finally:
        db.close()
    assert result["created"] is True
    assert result["outcome"] == "passed"
    assert receipt is not None
    assert receipt.outcome == "passed"
    assert before_jobs == after_jobs
    assert before_provider_operations == after_provider_operations
    assert PHONE not in receipt.evidence_json
    assert '"external_actions":0' in receipt.evidence_json
    assert '"provider_requests":0' in receipt.evidence_json


def test_drill_execution_key_is_idempotent_and_cannot_duplicate_evidence():
    db = SessionLocal()
    try:
        first = run_deterministic_drill(
            db,
            tenant_id="varun",
            fixture_type="expired_lease",
            execution_key="same-controlled-drill",
            now=NOW,
        )
        db.commit()
        second = run_deterministic_drill(
            db,
            tenant_id="varun",
            fixture_type="expired_lease",
            execution_key="same-controlled-drill",
            now=NOW,
        )
        count = db.query(DrillResult).filter(DrillResult.tenant_id == "varun").count()
    finally:
        db.close()
    assert first["created"] is True
    assert second == {"id": first["id"], "created": False, "outcome": "passed"}
    assert count == 1


def test_drill_list_is_tenant_isolated_and_redacts_internal_execution_key():
    db = SessionLocal()
    try:
        run_deterministic_drill(
            db,
            tenant_id="varun",
            fixture_type="callback_anomaly",
            execution_key="internal-runbook-key",
            now=NOW,
        )
        db.commit()
        varun = list_drill_results(db, tenant_id="varun")
        amul = list_drill_results(db, tenant_id="amul")
    finally:
        db.close()
    assert len(varun["results"]) == 1
    assert amul["results"] == []
    assert "execution_key" not in varun["results"][0]
    assert "internal-runbook-key" not in str(varun["results"][0])


def test_recovery_preview_is_read_only_non_executable_and_does_not_create_work():
    db = SessionLocal()
    try:
        db.add(_expired_campaign_job())
        db.commit()
        before_jobs = db.query(JobRun).count()
        before_drills = db.query(DrillResult).count()
        preview = recovery_plan_preview(db, tenant_id="varun", now=NOW)
        after_jobs = db.query(JobRun).count()
        after_drills = db.query(DrillResult).count()
    finally:
        db.close()
    assert preview["read_only"] is True
    assert preview["can_execute_from_browser"] is False
    assert preview["external_actions"] == 0
    assert preview["worker_activation_available"] is False
    assert preview["provider_access_available"] is False
    assert all(item["execution"] == "human_review_only" for item in preview["recommended_actions"])
    assert before_jobs == after_jobs == 1
    assert before_drills == after_drills == 0


def test_reliability_http_surface_is_get_only_and_tenant_safe():
    with TestClient(create_app()) as client:
        slos = client.get("/api/reliability/varun/slos")
        drills = client.get("/api/reliability/varun/drills")
        recovery = client.get("/api/reliability/varun/recovery-preview")
        post = client.post("/api/reliability/varun/drills")
        unknown = client.get("/api/reliability/not-a-tenant/slos")
    assert slos.status_code == 200
    assert slos.json()["read_only"] is True
    assert drills.status_code == 200
    assert drills.json()["results"] == []
    assert recovery.status_code == 200
    assert recovery.json()["can_execute_from_browser"] is False
    assert post.status_code == 405
    assert unknown.status_code == 404
