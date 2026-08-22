"""Day 28 tests for transactional outbox relay ownership and recovery."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from voxflow_api.db import JobOutbox, SessionLocal, reset_db
from voxflow_api.jobs.enqueue import enqueue_campaign_target
from voxflow_api.jobs.outbox import OutboxRelay, claim_outbox_events, mark_outbox_published
from voxflow_api.seed import seed


@pytest.fixture(autouse=True)
def fresh_database():
    reset_db()
    seed(reset=True)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _enqueue_outbox(queue_id: str) -> str:
    db = SessionLocal()
    try:
        result = enqueue_campaign_target(
            db,
            tenant_id="varun",
            campaign_id="cmp-day28",
            campaign_queue_id=queue_id,
        )
        db.commit()
        return result.outbox_id
    finally:
        db.close()


def _outbox(event_id: str) -> JobOutbox:
    db = SessionLocal()
    try:
        return db.get(JobOutbox, event_id)
    finally:
        db.close()


def test_relay_publishes_committed_event_once_and_records_publication():
    event_id = _enqueue_outbox("cq-day28-publish")
    delivered = []
    relay = OutboxRelay(
        session_factory=SessionLocal,
        publisher=delivered.append,
        relay_id="relay-a",
        now=_now,
    )

    result = relay.run_once()

    assert result.claimed == 1
    assert result.published == 1
    assert result.failed == 0
    assert [event.id for event in delivered] == [event_id]
    event = _outbox(event_id)
    assert event.published_at is not None
    assert event.relay_owner is None
    assert event.publish_attempt == 1


def test_failed_publish_is_released_and_a_second_relay_recovers_with_same_event_identity():
    event_id = _enqueue_outbox("cq-day28-retry")

    def failing_publisher(_event):
        raise RuntimeError("temporary consumer outage")

    first = OutboxRelay(
        session_factory=SessionLocal,
        publisher=failing_publisher,
        relay_id="relay-fail",
        now=_now,
    )
    first_result = first.run_once()
    after_failure = _outbox(event_id)

    assert first_result.failed == 1
    assert after_failure.published_at is None
    assert after_failure.relay_owner is None
    assert after_failure.last_error_code == "publish_failed"
    assert after_failure.publish_attempt == 1

    delivered = []
    second = OutboxRelay(
        session_factory=SessionLocal,
        publisher=delivered.append,
        relay_id="relay-recover",
        now=lambda: _now() + timedelta(seconds=1),
    )
    second_result = second.run_once()

    assert second_result.published == 1
    assert delivered[0].id == event_id
    assert delivered[0].idempotency_key == "campaign-target:cq-day28-retry"
    assert _outbox(event_id).publish_attempt == 2


def test_stale_relay_cannot_mark_event_published_after_its_lease_expires():
    event_id = _enqueue_outbox("cq-day28-stale")
    db = SessionLocal()
    try:
        claimed = claim_outbox_events(
            db,
            relay_id="relay-old",
            batch_size=1,
            lease_seconds=10,
            now=_now(),
        )
        db.commit()
    finally:
        db.close()

    assert [event.id for event in claimed] == [event_id]

    db = SessionLocal()
    try:
        stale_result = mark_outbox_published(
            db,
            event_id=event_id,
            relay_id="relay-old",
            now=_now() + timedelta(seconds=11),
        )
        db.commit()
    finally:
        db.close()

    assert stale_result is False
    assert _outbox(event_id).published_at is None
