"""Day 25 tests for durable campaign enqueueing and transactional outbox state."""

from __future__ import annotations

import json

import pytest

from voxflow_api.db import JobOutbox, JobRun, SessionLocal, reset_db
from voxflow_api.jobs.enqueue import campaign_target_idempotency_key, enqueue_campaign_target
from voxflow_api.seed import seed


@pytest.fixture(autouse=True)
def fresh_database():
    reset_db()
    seed(reset=True)


def test_campaign_target_enqueue_is_idempotent_within_one_transaction():
    db = SessionLocal()
    try:
        first = enqueue_campaign_target(
            db,
            tenant_id="varun",
            campaign_id="cmp-day25",
            campaign_queue_id="cq-day25-001",
            priority=7,
            trace_id="trace-day25",
        )
        second = enqueue_campaign_target(
            db,
            tenant_id="varun",
            campaign_id="cmp-day25",
            campaign_queue_id="cq-day25-001",
            priority=7,
            trace_id="trace-day25",
        )
        db.commit()

        assert first.created is True
        assert second.created is False
        assert second.job_id == first.job_id
        assert second.outbox_id == first.outbox_id
    finally:
        db.close()

    db = SessionLocal()
    try:
        jobs = db.query(JobRun).filter(JobRun.tenant_id == "varun").all()
        outbox = db.query(JobOutbox).filter(JobOutbox.tenant_id == "varun").all()

        assert len(jobs) == 1
        assert len(outbox) == 1
        assert jobs[0].status == "ready"
        assert jobs[0].job_type == "campaign.target.dispatch"
        assert jobs[0].priority == 7
        assert jobs[0].trace_id == "trace-day25"
        assert jobs[0].idempotency_key == campaign_target_idempotency_key("cq-day25-001")
        assert json.loads(jobs[0].payload_json) == {
            "campaign_id": "cmp-day25",
            "campaign_queue_id": "cq-day25-001",
        }
        assert outbox[0].event_type == "campaign.target.queued"
        assert outbox[0].aggregate_id == "cq-day25-001"
        assert outbox[0].published_at is None
    finally:
        db.close()


def test_campaign_target_enqueue_keeps_tenants_isolated():
    db = SessionLocal()
    try:
        first = enqueue_campaign_target(
            db,
            tenant_id="varun",
            campaign_id="cmp-varun",
            campaign_queue_id="cq-shared-reference",
        )
        second = enqueue_campaign_target(
            db,
            tenant_id="amul",
            campaign_id="cmp-amul",
            campaign_queue_id="cq-shared-reference",
        )
        db.commit()

        assert first.created is True
        assert second.created is True
        assert first.job_id != second.job_id
    finally:
        db.close()


def test_campaign_route_creates_one_job_and_outbox_record_per_target():
    from fastapi.testclient import TestClient

    from voxflow_api.main import create_app

    client = TestClient(create_app())
    response = client.post(
        "/api/campaigns?tenant_id=varun",
        json={
            "name": "Day 25 Durable Queue Test",
            "campaign_type": "delayed_shipment",
            "targets": [
                {"phone": "+919876543210", "name": "Sharma Logistics"},
                {"phone": "+919876543211", "name": "Gupta Distributors"},
            ],
            "auto_start": False,
        },
    )

    assert response.status_code == 200
    campaign_id = response.json()["id"]

    db = SessionLocal()
    try:
        jobs = db.query(JobRun).filter(JobRun.tenant_id == "varun").all()
        outbox = db.query(JobOutbox).filter(JobOutbox.tenant_id == "varun").all()

        assert len(jobs) == 2
        assert len(outbox) == 2
        assert {json.loads(job.payload_json)["campaign_id"] for job in jobs} == {campaign_id}
        assert {event.aggregate_type for event in outbox} == {"campaign_queue"}
    finally:
        db.close()
