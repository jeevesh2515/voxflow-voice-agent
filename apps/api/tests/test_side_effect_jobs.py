"""Day 34 tests for typed durable operational side effects."""

from __future__ import annotations

import json

import pytest

from voxflow_api.db import JobOutbox, JobRun, SessionLocal, SideEffectIntent, WorksheetLog, reset_db
from voxflow_api.jobs.side_effect_worker_service import SideEffectHandler, build_side_effects_worker
from voxflow_api.jobs.side_effects import (
    SHEETS_CALL_OUTCOME,
    enqueue_side_effect,
)
from voxflow_api.seed import seed


@pytest.fixture(autouse=True)
def fresh_database():
    reset_db()
    seed(reset=True)


def _worksheet_log(db, tenant_id: str = "varun") -> WorksheetLog:
    row = WorksheetLog(
        tenant_id=tenant_id,
        worksheet_name="Call Log",
        action_type="append",
        row_data_json=json.dumps({"call_id": f"call-{tenant_id}", "reason": "fixture"}),
    )
    db.add(row)
    db.flush()
    return row


def test_side_effect_enqueue_is_atomic_idempotent_and_redacted():
    db = SessionLocal()
    try:
        row = _worksheet_log(db)
        first = enqueue_side_effect(
            db,
            tenant_id="varun",
            effect_type=SHEETS_CALL_OUTCOME,
            aggregate_type="worksheet_log",
            aggregate_id=str(row.id),
            idempotency_key=f"sheets-call:{row.id}",
            trace_id="trace-day34",
        )
        second = enqueue_side_effect(
            db,
            tenant_id="varun",
            effect_type=SHEETS_CALL_OUTCOME,
            aggregate_type="worksheet_log",
            aggregate_id=str(row.id),
            idempotency_key=f"sheets-call:{row.id}",
            trace_id="trace-day34",
        )
        db.commit()
    finally:
        db.close()

    assert first.created is True
    assert second.created is False
    assert second.intent_id == first.intent_id
    assert second.job_id == first.job_id

    db = SessionLocal()
    try:
        intent = db.get(SideEffectIntent, first.intent_id)
        job = db.get(JobRun, first.job_id)
        outbox = db.get(JobOutbox, first.outbox_id)
        assert intent is not None and job is not None and outbox is not None
        assert intent.status == "queued"
        assert intent.effect_type == SHEETS_CALL_OUTCOME
        assert len(intent.payload_hash) == 64
        assert json.loads(job.payload_json) == {"side_effect_intent_id": first.intent_id}
        assert "reason" not in job.payload_json
        assert outbox.event_type == "sheets.call_outcome.append.queued"
    finally:
        db.close()


def test_side_effect_enqueue_keeps_tenants_isolated_with_same_reference():
    db = SessionLocal()
    try:
        varun_row = _worksheet_log(db, "varun")
        amul_row = _worksheet_log(db, "amul")
        varun = enqueue_side_effect(
            db,
            tenant_id="varun",
            effect_type=SHEETS_CALL_OUTCOME,
            aggregate_type="worksheet_log",
            aggregate_id=str(varun_row.id),
            idempotency_key="sheets-call:shared-reference",
        )
        amul = enqueue_side_effect(
            db,
            tenant_id="amul",
            effect_type=SHEETS_CALL_OUTCOME,
            aggregate_type="worksheet_log",
            aggregate_id=str(amul_row.id),
            idempotency_key="sheets-call:shared-reference",
        )
        db.commit()
    finally:
        db.close()

    assert varun.intent_id != amul.intent_id
    assert varun.job_id != amul.job_id


def test_side_effect_worker_remains_disabled_without_explicit_gate(monkeypatch):
    monkeypatch.setattr(
        "voxflow_api.jobs.side_effect_worker_service.durable_side_effects_worker_enabled",
        lambda: False,
    )
    assert build_side_effects_worker() is None


def test_dry_run_worker_marks_intent_without_sheets_or_provider_io(monkeypatch):
    db = SessionLocal()
    try:
        row = _worksheet_log(db)
        result = enqueue_side_effect(
            db,
            tenant_id="varun",
            effect_type=SHEETS_CALL_OUTCOME,
            aggregate_type="worksheet_log",
            aggregate_id=str(row.id),
            idempotency_key=f"sheets-call:{row.id}",
        )
        db.commit()
    finally:
        db.close()

    class _UnexpectedSheets:
        def append_call_outcome(self, *_args, **_kwargs):  # pragma: no cover - test fails before awaiting
            raise AssertionError("dry-run worker must not call Sheets")

    monkeypatch.setattr(
        "voxflow_api.jobs.side_effect_worker_service.durable_side_effects_worker_enabled",
        lambda: True,
    )
    monkeypatch.setattr(
        "voxflow_api.jobs.side_effect_worker_service.side_effects_tenant_ids",
        lambda: ("varun",),
    )
    monkeypatch.setattr(
        "voxflow_api.jobs.side_effect_worker_service.durable_side_effects_dry_run",
        lambda: True,
    )
    monkeypatch.setattr(
        "voxflow_api.jobs.side_effect_worker_service.get_sheets_client",
        lambda: _UnexpectedSheets(),
    )

    worker = build_side_effects_worker()
    assert worker is not None
    outcome = worker.run_once()
    assert outcome.succeeded == 1

    db = SessionLocal()
    try:
        intent = db.get(SideEffectIntent, result.intent_id)
        job = db.get(JobRun, result.job_id)
        assert intent is not None and intent.status == "dry_run"
        assert intent.result_code == "side_effect_dry_run"
        assert job is not None and job.status == "succeeded"
    finally:
        db.close()


def test_retryable_sheets_failure_preserves_intent_and_schedules_retry(monkeypatch):
    db = SessionLocal()
    try:
        row = _worksheet_log(db)
        result = enqueue_side_effect(
            db,
            tenant_id="varun",
            effect_type=SHEETS_CALL_OUTCOME,
            aggregate_type="worksheet_log",
            aggregate_id=str(row.id),
            idempotency_key=f"sheets-call:{row.id}",
        )
        db.commit()
    finally:
        db.close()

    class _UnavailableSheets:
        @staticmethod
        async def append_call_outcome(*_args, **_kwargs):
            return {"ok": False, "reason": "http_503"}

    monkeypatch.setattr(
        "voxflow_api.jobs.side_effect_worker_service.durable_side_effects_worker_enabled",
        lambda: True,
    )
    monkeypatch.setattr(
        "voxflow_api.jobs.side_effect_worker_service.side_effects_tenant_ids",
        lambda: ("varun",),
    )
    monkeypatch.setattr(
        "voxflow_api.jobs.side_effect_worker_service.durable_side_effects_dry_run",
        lambda: False,
    )
    monkeypatch.setattr(
        "voxflow_api.jobs.side_effect_worker_service.get_sheets_client",
        lambda: _UnavailableSheets(),
    )

    worker = build_side_effects_worker()
    assert worker is not None
    outcome = worker.run_once()
    assert outcome.retried == 1

    db = SessionLocal()
    try:
        intent = db.get(SideEffectIntent, result.intent_id)
        job = db.get(JobRun, result.job_id)
        assert intent is not None and intent.status == "retry_scheduled"
        assert intent.result_code == "http_503"
        assert job is not None and job.status == "retry_scheduled"
    finally:
        db.close()


def test_handler_rejects_untrusted_intent_job_mismatch():
    handler = SideEffectHandler()
    from voxflow_api.jobs.retry import PermanentJobError
    from voxflow_api.jobs.worker import JobContext

    context = JobContext(
        job_id="wrong-job",
        tenant_id="varun",
        job_type=SHEETS_CALL_OUTCOME,
        attempt=1,
        trace_id=None,
        worker_id="test",
        idempotency_key="test",
        payload={"side_effect_intent_id": "missing"},
        renew_lease=lambda: True,
    )
    with pytest.raises(PermanentJobError, match="intent was not found"):
        handler(context)


def test_manual_email_endpoint_queues_durable_scan_without_running_agent(monkeypatch):
    from fastapi.testclient import TestClient

    from voxflow_api.main import create_app

    with TestClient(create_app()) as client:
        response = client.post("/api/admin/email-summarizer/run?tenant_id=varun&limit=7")

    assert response.status_code == 200
    payload = response.json()
    assert payload["queued"] is True
    assert payload["limit"] == 7
    db = SessionLocal()
    try:
        job = db.get(JobRun, payload["job_id"])
        assert job is not None
        assert job.job_type == "email.summarization.scan"
        assert job.status == "ready"
    finally:
        db.close()


def test_direct_outbound_tool_is_rejected_without_provider_invocation():
    import asyncio
    from types import SimpleNamespace

    from voxflow_api.agent.tools import place_outbound_call

    result = asyncio.run(
        place_outbound_call(
            SimpleNamespace(tenant_id="varun", call_id="call-day34-safety"),
            to_phone="+919999999999",
            instruction="Never dispatch directly",
        )
    )
    assert result["ok"] is False
    assert result["error"] == "direct_outbound_calls_disabled"


def test_alert_notification_worker_dispatches_bounded_webhook(monkeypatch):
    from voxflow_api.services.alerting_service import dispatch_alert_notification

    captured: dict = {}

    async def _fake_dispatch_webhook(tenant_id: str, event_type: str, payload: dict) -> bool:
        captured["tenant_id"] = tenant_id
        captured["event_type"] = event_type
        captured["payload"] = dict(payload)
        return True

    monkeypatch.setattr(
        "voxflow_api.jobs.side_effect_worker_service.dispatch_webhook",
        _fake_dispatch_webhook,
    )
    monkeypatch.setattr(
        "voxflow_api.jobs.side_effect_worker_service.durable_side_effects_worker_enabled",
        lambda: True,
    )
    monkeypatch.setattr(
        "voxflow_api.jobs.side_effect_worker_service.side_effects_tenant_ids",
        lambda: ("varun",),
    )
    monkeypatch.setattr(
        "voxflow_api.jobs.side_effect_worker_service.durable_side_effects_dry_run",
        lambda: False,
    )

    db = SessionLocal()
    try:
        receipt = dispatch_alert_notification(
            db,
            tenant_id="varun",
            evaluation={
                "alerts": [{"code": "high_cpu"}, {"code": "node_down"}],
                "state": "critical",
                "summary": ["secret context that must not leave the app"],
            },
        )
        db.commit()
    finally:
        db.close()

    assert receipt["queued"] is True
    assert receipt["execution"] == "durable_worker_owned"

    worker = build_side_effects_worker()
    assert worker is not None
    outcome = worker.run_once()
    assert outcome.succeeded == 1

    assert captured["tenant_id"] == "varun"
    assert captured["event_type"] == "observability_alert"
    assert captured["payload"] == {
        "alert_codes": ["high_cpu", "node_down"],
        "state": "critical",
    }

    db = SessionLocal()
    try:
        intent = db.get(SideEffectIntent, receipt["intent_id"])
        job = db.get(JobRun, receipt["job_id"])
        assert intent is not None and intent.status == "succeeded"
        assert intent.result_code == "side_effect_succeeded"
        assert job is not None and job.status == "succeeded"
    finally:
        db.close()
