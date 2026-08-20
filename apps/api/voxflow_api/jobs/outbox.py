"""Day 28 transactional outbox relay.

The relay owns no business state. It claims committed, unpublished events with a
short lease, calls an idempotent publisher outside the claim transaction, then
conditionally marks the event published. A relay crash leaves the event eligible
for recovery after its lease expires.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import or_, update
from sqlalchemy.orm import Session, sessionmaker

from ..db import JobOutbox
from .repository import utcnow


@dataclass(frozen=True)
class OutboxEvent:
    """Sanitised immutable event delivered to an idempotent publisher."""

    id: str
    tenant_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    idempotency_key: str
    payload: dict[str, object]
    publish_attempt: int


@dataclass(frozen=True)
class RelayRunResult:
    """Counters from one bounded relay iteration."""

    claimed: int = 0
    published: int = 0
    failed: int = 0
    stale: int = 0


OutboxPublisher = Callable[[OutboxEvent], None]


def build_relay_id() -> str:
    """Return a unique process identity used for relay lease ownership."""

    return f"relay:{uuid.uuid4().hex[:16]}"


def _event_from_row(row: JobOutbox) -> OutboxEvent:
    try:
        payload = json.loads(row.payload_json or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("outbox payload is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("outbox payload must be a JSON object")
    return OutboxEvent(
        id=row.id,
        tenant_id=row.tenant_id,
        event_type=row.event_type,
        aggregate_type=row.aggregate_type,
        aggregate_id=row.aggregate_id,
        idempotency_key=row.idempotency_key,
        payload=payload,
        publish_attempt=row.publish_attempt,
    )


def claim_outbox_events(
    db: Session,
    *,
    relay_id: str,
    batch_size: int,
    lease_seconds: int = 60,
    now: datetime | None = None,
) -> list[OutboxEvent]:
    """Atomically lease unpublished events for one relay process."""

    if not relay_id.strip():
        raise ValueError("relay_id is required")
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    if lease_seconds < 1:
        raise ValueError("lease_seconds must be at least 1")

    claimed_at = now or utcnow()
    query = (
        db.query(JobOutbox)
        .filter(
            JobOutbox.published_at.is_(None),
            or_(
                JobOutbox.relay_lease_expires_at.is_(None),
                JobOutbox.relay_lease_expires_at <= claimed_at,
            ),
        )
        .order_by(JobOutbox.created_at.asc(), JobOutbox.id.asc())
    )
    if db.get_bind().dialect.name != "sqlite":
        query = query.with_for_update(skip_locked=True)

    rows = query.limit(batch_size).all()
    lease_expires_at = claimed_at + timedelta(seconds=lease_seconds)
    for row in rows:
        row.relay_owner = relay_id
        row.relay_lease_expires_at = lease_expires_at
        row.publish_attempt += 1
        row.last_error_code = None
        row.last_error_json = None
    db.flush()
    return [_event_from_row(row) for row in rows]


def mark_outbox_published(
    db: Session,
    *,
    event_id: str,
    relay_id: str,
    now: datetime | None = None,
) -> bool:
    """Mark an event published only if this relay still owns an active lease."""

    published_at = now or utcnow()
    result = db.execute(
        update(JobOutbox)
        .where(
            JobOutbox.id == event_id,
            JobOutbox.published_at.is_(None),
            JobOutbox.relay_owner == relay_id,
            JobOutbox.relay_lease_expires_at > published_at,
        )
        .values(
            published_at=published_at,
            relay_owner=None,
            relay_lease_expires_at=None,
        )
    )
    db.flush()
    return result.rowcount == 1


def release_outbox_event(
    db: Session,
    *,
    event_id: str,
    relay_id: str,
    error_code: str,
    error_detail: str = "",
    now: datetime | None = None,
) -> bool:
    """Release an active relay lease after a publish failure for later recovery."""

    released_at = now or utcnow()
    error_json = json.dumps({"detail": error_detail}, sort_keys=True) if error_detail else None
    result = db.execute(
        update(JobOutbox)
        .where(
            JobOutbox.id == event_id,
            JobOutbox.published_at.is_(None),
            JobOutbox.relay_owner == relay_id,
            JobOutbox.relay_lease_expires_at > released_at,
        )
        .values(
            relay_owner=None,
            relay_lease_expires_at=None,
            last_error_code=error_code,
            last_error_json=error_json,
        )
    )
    db.flush()
    return result.rowcount == 1


class OutboxRelay:
    """Bounded relay runtime for publisher adapters with idempotent consumers."""

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        publisher: OutboxPublisher,
        relay_id: str | None = None,
        batch_size: int = 20,
        lease_seconds: int = 60,
        now: Callable[[], datetime] = utcnow,
    ) -> None:
        self.session_factory = session_factory
        self.publisher = publisher
        self.relay_id = relay_id or build_relay_id()
        self.batch_size = batch_size
        self.lease_seconds = lease_seconds
        self.now = now

    def _transition(self, event_id: str, *, published: bool, error: Exception | None = None) -> bool:
        db = self.session_factory()
        try:
            if published:
                changed = mark_outbox_published(db, event_id=event_id, relay_id=self.relay_id, now=self.now())
            else:
                changed = release_outbox_event(
                    db,
                    event_id=event_id,
                    relay_id=self.relay_id,
                    error_code="publish_failed",
                    error_detail=str(error) if error else "",
                    now=self.now(),
                )
            db.commit()
            return changed
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def run_once(self) -> RelayRunResult:
        """Publish one safely claimed batch without holding database locks in I/O."""

        db = self.session_factory()
        try:
            events = claim_outbox_events(
                db,
                relay_id=self.relay_id,
                batch_size=self.batch_size,
                lease_seconds=self.lease_seconds,
                now=self.now(),
            )
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

        published = failed = stale = 0
        for event in events:
            try:
                self.publisher(event)
            except Exception as exc:
                if self._transition(event.id, published=False, error=exc):
                    failed += 1
                else:
                    stale += 1
            else:
                if self._transition(event.id, published=True):
                    published += 1
                else:
                    stale += 1
        return RelayRunResult(claimed=len(events), published=published, failed=failed, stale=stale)
