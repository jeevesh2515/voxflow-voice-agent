"""End-to-end Day 30 campaign dispatch policy tests with a mocked provider."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from voxflow_api.db import (
    CampaignPolicyDecision,
    CampaignQueue,
    JobAttempt,
    JobRun,
    OutboundCampaign,
    RecipientCampaignPreference,
    SessionLocal,
    TenantCampaignPolicy,
    TenantDailyDispatchUsage,
    reset_db,
)
from voxflow_api.jobs.campaign_dispatch import CampaignDispatchHandler
from voxflow_api.jobs.worker import WorkerRuntime
from voxflow_api.seed import seed

TEST_NOW = datetime(2026, 8, 20, 10, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def fresh_database():
    reset_db()
    seed(reset=True)


def _create_target(
    *,
    suffix: str,
    campaign_status: str = "active",
    consent_status: str = "granted",
    opted_out: bool = False,
    window_start: str = "00:00",
    window_end: str = "23:59",
    daily_call_limit: int = 10,
    max_in_flight: int = 2,
) -> tuple[str, str, str]:
    campaign_id = f"cmp-policy-{suffix}"
    queue_id = f"cq-policy-{suffix}"
    job_id = f"job-policy-{suffix}"
    phone = f"+91987654{int(suffix):04d}"
    db = SessionLocal()
    try:
        db.add_all(
            [
                OutboundCampaign(
                    id=campaign_id,
                    tenant_id="varun",
                    name=f"Policy campaign {suffix}",
                    campaign_type="po_confirmation",
                    status=campaign_status,
                    total_targets=1,
                ),
                CampaignQueue(
                    id=queue_id,
                    campaign_id=campaign_id,
                    tenant_id="varun",
                    recipient_phone=phone,
                    recipient_name="Policy Supplier",
                    context_data_json='{"po_id":"PO-30","quantity":12}',
                    status="queued",
                ),
                JobRun(
                    id=job_id,
                    tenant_id="varun",
                    job_type="campaign.target.dispatch",
                    payload_json=json.dumps({"campaign_id": campaign_id, "campaign_queue_id": queue_id}),
                    status="ready",
                    priority=0,
                    idempotency_key=f"campaign-target:{queue_id}",
                    scheduled_at=TEST_NOW - timedelta(seconds=1),
                    next_run_at=TEST_NOW - timedelta(seconds=1),
                    max_attempts=5,
                ),
                RecipientCampaignPreference(
                    id=f"pref-policy-{suffix}",
                    tenant_id="varun",
                    recipient_phone=phone,
                    consent_status=consent_status,
                    consent_purpose="outbound_campaign",
                    opted_out=int(opted_out),
                    source="day30-test",
                ),
            ]
        )
        policy = db.get(TenantCampaignPolicy, "varun")
        if policy is None:
            db.add(
                TenantCampaignPolicy(
                    tenant_id="varun",
                    timezone_name="UTC",
                    calling_window_start=window_start,
                    calling_window_end=window_end,
                    daily_call_limit=daily_call_limit,
                    max_in_flight=max_in_flight,
                    enabled=1,
                )
            )
        else:
            policy.timezone_name = "UTC"
            policy.calling_window_start = window_start
            policy.calling_window_end = window_end
            policy.daily_call_limit = daily_call_limit
            policy.max_in_flight = max_in_flight
            policy.enabled = 1
        db.commit()
    finally:
        db.close()
    return campaign_id, queue_id, job_id


def _run_one(*, provider_calls: list[tuple[str, str]], dry_run: bool = False) -> object:
    handler = CampaignDispatchHandler(
        session_factory=SessionLocal,
        provider_call=lambda phone, instruction: provider_calls.append((phone, instruction)) or {"ok": True, "call": {"id": "policy-call"}},
        dry_run=lambda: dry_run,
        now=lambda: TEST_NOW,
    )
    worker = WorkerRuntime(
        session_factory=SessionLocal,
        handlers={"campaign.target.dispatch": handler},
        worker_id="day30-policy",
        job_types=("campaign.target.dispatch",),
        tenant_ids=("varun",),
        batch_size=1,
        now=lambda: TEST_NOW,
        base_retry_seconds=0.001,
    )
    return worker.run_once()


def _get(model, row_id: str):
    db = SessionLocal()
    try:
        return db.get(model, row_id)
    finally:
        db.close()


def _job_attempt(job_id: str) -> JobAttempt:
    db = SessionLocal()
    try:
        return db.query(JobAttempt).filter(JobAttempt.job_id == job_id).one()
    finally:
        db.close()


def _usage() -> TenantDailyDispatchUsage:
    db = SessionLocal()
    try:
        return db.query(TenantDailyDispatchUsage).filter(TenantDailyDispatchUsage.tenant_id == "varun").one()
    finally:
        db.close()


def _decision_codes(job_id: str) -> list[str]:
    db = SessionLocal()
    try:
        return [
            row.reason_code
            for row in db.query(CampaignPolicyDecision)
            .filter(CampaignPolicyDecision.job_id == job_id)
            .order_by(CampaignPolicyDecision.created_at.asc())
            .all()
        ]
    finally:
        db.close()


def test_paused_campaign_is_auditable_terminal_cancellation_without_provider_call():
    _, queue_id, job_id = _create_target(suffix="1", campaign_status="paused")
    provider_calls: list[tuple[str, str]] = []

    result = _run_one(provider_calls=provider_calls)

    assert result.cancelled == 1
    assert result.retried == 0
    assert provider_calls == []
    assert _get(JobRun, job_id).status == "cancelled"
    assert _get(JobRun, job_id).last_error_code == "campaign_not_active"
    assert _get(CampaignQueue, queue_id).status == "cancelled"
    assert _decision_codes(job_id) == ["campaign_not_active"]


def test_outside_local_business_window_defers_to_exact_next_window_without_provider_call():
    _, queue_id, job_id = _create_target(suffix="2", window_start="11:00", window_end="18:00")
    provider_calls: list[tuple[str, str]] = []

    result = _run_one(provider_calls=provider_calls)

    job = _get(JobRun, job_id)
    attempt = _job_attempt(job_id)
    assert result.deferred == 1
    assert provider_calls == []
    assert job.status == "retry_scheduled"
    assert job.last_error_code == "outside_calling_window"
    assert job.next_run_at is not None
    assert job.next_run_at.replace(tzinfo=timezone.utc) == datetime(2026, 8, 20, 11, 0, tzinfo=timezone.utc)
    assert job.max_attempts == 6
    assert attempt.outcome == "policy_deferred"
    assert _get(CampaignQueue, queue_id).status == "queued"
    assert _decision_codes(job_id) == ["outside_calling_window"]


def test_consent_withdrawal_and_opt_out_are_terminal_and_never_reach_provider():
    _, withdrawn_queue, withdrawn_job = _create_target(suffix="3", consent_status="withdrawn")
    _, opted_out_queue, opted_out_job = _create_target(suffix="4", opted_out=True)
    provider_calls: list[tuple[str, str]] = []

    result = _run_one(provider_calls=provider_calls)
    second = _run_one(provider_calls=provider_calls)

    assert result.cancelled == 1
    assert second.cancelled == 1
    assert provider_calls == []
    assert _get(JobRun, withdrawn_job).status == "cancelled"
    assert _get(CampaignQueue, withdrawn_queue).status == "cancelled"
    assert _decision_codes(withdrawn_job) == ["consent_not_granted"]
    assert _get(JobRun, opted_out_job).status == "cancelled"
    assert _get(CampaignQueue, opted_out_queue).status == "cancelled"
    assert _decision_codes(opted_out_job) == ["recipient_opted_out"]


def test_daily_budget_defers_second_target_without_duplicate_provider_effect():
    _create_target(suffix="5", daily_call_limit=1, max_in_flight=1)
    _, second_queue, second_job = _create_target(suffix="6", daily_call_limit=1, max_in_flight=1)
    provider_calls: list[tuple[str, str]] = []

    first = _run_one(provider_calls=provider_calls)
    second = _run_one(provider_calls=provider_calls)

    usage = _usage()
    assert first.retried == 1
    assert second.deferred == 1
    assert len(provider_calls) == 1
    assert _get(JobRun, second_job).status == "retry_scheduled"
    assert _get(JobRun, second_job).last_error_code == "daily_call_budget_exhausted"
    assert _get(CampaignQueue, second_queue).status == "queued"
    assert usage.reserved_calls == 1
    assert usage.active_dispatches == 1
    assert _decision_codes(second_job) == ["policy_allowed", "daily_call_budget_exhausted"]
