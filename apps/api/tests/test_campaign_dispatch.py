"""Day 29 durable campaign-worker end-to-end execution tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from voxflow_api.db import CampaignQueue, JobRun, ProviderOperation, SessionLocal, reset_db
from voxflow_api.jobs.campaign_dispatch import CampaignDispatchHandler
from voxflow_api.jobs.reconciliation import reconcile_campaign_provider_operation
from voxflow_api.jobs.worker import WorkerRuntime
from voxflow_api.seed import seed


@pytest.fixture(autouse=True)
def fresh_database():
    reset_db()
    seed(reset=True)


def _create_campaign_target(*, campaign_id: str, queue_id: str, job_id: str, status: str = "active") -> None:
    from voxflow_api.db import OutboundCampaign

    db = SessionLocal()
    try:
        campaign = OutboundCampaign(
            id=campaign_id,
            tenant_id="varun",
            name="Day 29 canary",
            campaign_type="po_confirmation",
            status=status,
            total_targets=1,
        )
        queue = CampaignQueue(
            id=queue_id,
            campaign_id=campaign_id,
            tenant_id="varun",
            recipient_phone="+919876543210",
            recipient_name="Canary Supplier",
            context_data_json='{"po_id":"PO-29","quantity":10}',
            status="queued",
        )
        job = JobRun(
            id=job_id,
            tenant_id="varun",
            job_type="campaign.target.dispatch",
            payload_json=f'{{"campaign_id":"{campaign_id}","campaign_queue_id":"{queue_id}"}}',
            status="ready",
            priority=0,
            idempotency_key=f"campaign-target:{queue_id}",
            max_attempts=5,
        )
        db.add_all([campaign, queue, job])
        db.commit()
    finally:
        db.close()


def _row(model, row_id: str):
    db = SessionLocal()
    try:
        return db.get(model, row_id)
    finally:
        db.close()


def test_dry_run_canary_completes_durable_target_without_provider_call():
    _create_campaign_target(campaign_id="cmp-dry", queue_id="cq-dry", job_id="job-dry")
    provider_calls = []
    handler = CampaignDispatchHandler(
        session_factory=SessionLocal,
        provider_call=lambda phone, instruction: provider_calls.append((phone, instruction)) or {"ok": True},
        dry_run=lambda: True,
    )
    worker = WorkerRuntime(
        session_factory=SessionLocal,
        handlers={"campaign.target.dispatch": handler},
        worker_id="canary-dry",
        job_types=("campaign.target.dispatch",),
        tenant_ids=("varun",),
    )

    result = worker.run_once()

    assert result.claimed == 1
    assert result.succeeded == 1
    assert provider_calls == []
    assert _row(JobRun, "job-dry").status == "succeeded"
    assert _row(CampaignQueue, "cq-dry").status == "completed"
    db = SessionLocal()
    try:
        operation = db.query(ProviderOperation).filter(ProviderOperation.tenant_id == "varun").one()
        assert operation.status == "dry_run"
        assert operation.provider_id.startswith("dry-")
    finally:
        db.close()


def test_real_canary_request_is_not_redialed_and_completes_after_reconciliation():
    _create_campaign_target(campaign_id="cmp-live", queue_id="cq-live", job_id="job-live")
    provider_calls = []

    def provider_call(phone: str, instruction: str):
        provider_calls.append((phone, instruction))
        return {"ok": True, "call": {"id": "dial-call-29"}}

    handler = CampaignDispatchHandler(session_factory=SessionLocal, provider_call=provider_call, dry_run=lambda: False)
    worker = WorkerRuntime(
        session_factory=SessionLocal,
        handlers={"campaign.target.dispatch": handler},
        worker_id="canary-live",
        job_types=("campaign.target.dispatch",),
        tenant_ids=("varun",),
        base_retry_seconds=0.001,
    )

    first = worker.run_once()
    assert first.retried == 1
    assert len(provider_calls) == 1
    assert _row(CampaignQueue, "cq-live").status == "dialing"

    db = SessionLocal()
    try:
        operation = db.query(ProviderOperation).filter(ProviderOperation.tenant_id == "varun").one()
        assert operation.status == "accepted"
        reconcile_campaign_provider_operation(
            db,
            operation_id=operation.id,
            provider_status="confirmed",
            provider_id="dial-call-29",
        )
        job = db.get(JobRun, "job-live")
        job.next_run_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    finally:
        db.close()

    second = worker.run_once()
    assert second.succeeded == 1
    assert len(provider_calls) == 1
    assert _row(JobRun, "job-live").status == "succeeded"
    assert _row(CampaignQueue, "cq-live").status == "completed"
