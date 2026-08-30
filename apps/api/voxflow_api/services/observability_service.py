"""Day 51 tenant-scoped observability, call-KPI, and subsystem health aggregation.

Every method in this module is read-only. It reads persisted tenant rows,
computes aggregates, and returns redacted payloads. It never contacts a
provider, sends a message, writes a sheet, starts a worker, or returns raw
transcript, caller phone, PIN, or order JSON to a caller.

Tenant scoping is enforced by the caller (``require_tenant_role``); every query
here additionally filters on ``tenant_id`` so a routing mistake cannot widen a
result set.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import time
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..benchmarks.engine import calculate_percentiles
from ..config import get_settings
from ..db import (
    Call,
    CommunicationLog,
    JobOutbox,
    JobRun,
    Tenant,
    TenantPhoneNumber,
    WorksheetLog,
)
from ..monitoring import scrub_value


MAX_RANGE_DAYS = 90
MAX_EVENT_LIMIT = 100

# A degraded/critical health verdict is derived from these subsystem states so
# the dashboard badge and the alerting engine can never disagree.
HEALTH_OPERATIONAL = "operational"
HEALTH_DEGRADED = "degraded"
HEALTH_CRITICAL = "critical"

_RESOLVED_OUTCOMES = frozenset({"completed"})
_ESCALATED_OUTCOMES = frozenset({"escalated"})


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _iso(value: datetime | None) -> str | None:
    utc_value = _as_utc(value)
    return utc_value.isoformat() if utc_value else None


def _percentage(numerator: int, denominator: int) -> float:
    return round((numerator / denominator) * 100, 1) if denominator else 0.0


def _delta_percent(current: int | float, previous: int | float) -> float | None:
    """Period-over-period change. ``None`` when there is no comparable baseline."""

    if not previous:
        return None
    return round(((current - previous) / previous) * 100, 1)


def _bucket(value: str | None, default: str = "unclassified") -> str:
    cleaned = (value or "").strip().lower().replace(" ", "_")
    return cleaned or default


def _is_resolved(call: Call) -> bool:
    return call.resolution_status == "resolved" or call.outcome in _RESOLVED_OUTCOMES


def _is_escalated(call: Call) -> bool:
    return bool(call.escalated) or call.outcome in _ESCALATED_OUTCOMES


def _clamp_days(time_range_days: int) -> int:
    """Bound a caller-supplied window. ``0`` clamps to 1 day, not to the default."""

    if time_range_days is None:
        return 7
    return max(1, min(int(time_range_days), MAX_RANGE_DAYS))


def _require_tenant(db: Session, tenant_id: str) -> Tenant:
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError("tenant_not_found")
    return tenant


def _calls_between(db: Session, tenant_id: str, start: datetime, end: datetime) -> list[Call]:
    return list(
        db.execute(
            select(Call).where(
                Call.tenant_id == tenant_id,
                Call.started_at >= start,
                Call.started_at < end,
            )
        )
        .scalars()
        .all()
    )


def _turn_latency_samples(calls: list[Call]) -> list[float]:
    """Persisted mean per-turn server latency, in milliseconds.

    Calls with no recorded latency (legacy rows, abandoned sessions) contribute
    no sample instead of a misleading zero.
    """

    return [float(call.avg_turn_latency_ms) for call in calls if (call.avg_turn_latency_ms or 0) > 0]


def get_call_kpis(db: Session, tenant_id: str, time_range_days: int = 7) -> dict[str, Any]:
    """Aggregate tenant call KPIs, latency percentiles, and daily volume buckets."""

    days = _clamp_days(time_range_days)
    tenant = _require_tenant(db, tenant_id)
    now = _utcnow()
    period_start = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    prior_start = period_start - timedelta(days=days)

    calls = _calls_between(db, tenant_id, period_start, now + timedelta(seconds=1))
    prior_calls = _calls_between(db, tenant_id, prior_start, period_start)

    total_calls = len(calls)
    resolved_calls = sum(1 for call in calls if _is_resolved(call))
    escalated_calls = sum(1 for call in calls if _is_escalated(call))
    total_duration = sum(call.duration_sec or 0 for call in calls)
    open_follow_ups = sum(1 for call in calls if call.follow_up_required and call.staff_resolved_at is None)
    verified_calls = sum(1 for call in calls if call.verified)
    breached = sum(
        1
        for call in calls
        if call.escalation_status in {"pending", "in_progress"}
        and call.sla_due_at is not None
        and (_as_utc(call.sla_due_at) or now) < now
    )

    prior_total = len(prior_calls)
    prior_resolved = sum(1 for call in prior_calls if _is_resolved(call))
    prior_escalated = sum(1 for call in prior_calls if _is_escalated(call))

    latency = calculate_percentiles(_turn_latency_samples(calls)).to_dict()
    prior_latency = calculate_percentiles(_turn_latency_samples(prior_calls)).to_dict()

    daily: dict[str, dict[str, Any]] = {}
    for offset in range(days):
        key = (period_start + timedelta(days=offset)).date().isoformat()
        daily[key] = {"date": key, "calls": 0, "resolved": 0, "escalated": 0, "duration_sec": 0}
    for call in calls:
        started = _as_utc(call.started_at)
        if started is None:
            continue
        bucket = daily.get(started.date().isoformat())
        if bucket is None:
            continue
        bucket["calls"] += 1
        bucket["duration_sec"] += call.duration_sec or 0
        if _is_resolved(call):
            bucket["resolved"] += 1
        if _is_escalated(call):
            bucket["escalated"] += 1

    return {
        "tenant_id": tenant.id,
        "tenant_name": tenant.name,
        "period": {
            "days": days,
            "from": period_start.date().isoformat(),
            "to": now.date().isoformat(),
            "generated_at": now.isoformat(),
            "comparison_from": prior_start.date().isoformat(),
        },
        "total_calls": total_calls,
        "resolved_calls": resolved_calls,
        "resolution_rate": _percentage(resolved_calls, total_calls),
        "escalated_calls": escalated_calls,
        "escalation_rate": _percentage(escalated_calls, total_calls),
        "open_follow_ups": open_follow_ups,
        "sla_breached_count": breached,
        "verified_call_rate": _percentage(verified_calls, total_calls),
        "avg_duration_sec": round(total_duration / total_calls) if total_calls else 0,
        "total_duration_sec": total_duration,
        "total_minutes": round(total_duration / 60, 2),
        "median_turn_latency_ms": round(latency["p50_ms"]),
        "p90_turn_latency_ms": round(latency["p90_ms"]),
        "p99_turn_latency_ms": round(latency["p99_ms"]),
        "latency_distribution": latency,
        "deltas": {
            "total_calls_pct": _delta_percent(total_calls, prior_total),
            "resolution_rate_pct": _delta_percent(
                _percentage(resolved_calls, total_calls), _percentage(prior_resolved, prior_total)
            ),
            "escalation_rate_pct": _delta_percent(
                _percentage(escalated_calls, total_calls), _percentage(prior_escalated, prior_total)
            ),
            "median_turn_latency_pct": _delta_percent(latency["p50_ms"], prior_latency["p50_ms"]),
            "prior_total_calls": prior_total,
        },
        "calls_over_time": list(daily.values()),
        "breakdown": {
            "reasons": dict(sorted(Counter(_bucket(call.intent, "general") for call in calls).items())),
            "resolution_categories": dict(
                sorted(Counter(_bucket(call.resolution_category, "uncategorized") for call in calls).items())
            ),
            "outcomes": dict(sorted(Counter(_bucket(call.outcome, "unknown") for call in calls).items())),
            "languages": dict(sorted(Counter(_bucket(call.language, "unknown") for call in calls).items())),
            "satisfaction": dict(sorted(Counter(_bucket(call.satisfaction, "not_scored") for call in calls).items())),
        },
    }


def _subsystem(
    key: str,
    label: str,
    status: str,
    *,
    latency_ms: float | None = None,
    detail: str = "",
) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "status": status,
        "latency_ms": round(latency_ms, 2) if latency_ms is not None else None,
        "detail": detail,
    }


def _measure_db_latency(db: Session) -> tuple[float | None, str]:
    """Round-trip one trivial statement on the live pooled connection."""

    started = time.perf_counter()
    try:
        db.execute(text("SELECT 1")).scalar_one()
    except Exception:
        return None, "unavailable"
    return (time.perf_counter() - started) * 1000.0, "ok"


def get_system_health_metrics(db: Session, tenant_id: str) -> dict[str, Any]:
    """Report tenant-scoped subsystem latency and durable-work health.

    The LLM figure is derived from *persisted* per-turn latency, deliberately
    not a live provider request: a dashboard poll must never bill a customer's
    Groq quota or block on a third-party timeout.
    """

    settings = get_settings()
    tenant = _require_tenant(db, tenant_id)
    now = _utcnow()
    day_ago = now - timedelta(hours=24)

    db_latency_ms, db_state = _measure_db_latency(db)

    jobs = list(db.execute(select(JobRun).where(JobRun.tenant_id == tenant_id)).scalars().all())
    outbox = list(db.execute(select(JobOutbox).where(JobOutbox.tenant_id == tenant_id)).scalars().all())
    recent_calls = _calls_between(db, tenant_id, day_ago, now + timedelta(seconds=1))

    outbox_pending = sum(1 for item in outbox if item.published_at is None)
    oldest_pending = min((_as_utc(item.created_at) for item in outbox if item.published_at is None), default=None)
    outbox_lag_sec = int((now - oldest_pending).total_seconds()) if oldest_pending else None

    dead_lettered = [job for job in jobs if job.status == "dead_lettered"]
    recent_dead_lettered = sum(1 for job in dead_lettered if (_as_utc(job.updated_at) or now) >= day_ago)
    expired_leases = sum(
        1
        for job in jobs
        if job.status == "running" and job.lease_expires_at is not None and (_as_utc(job.lease_expires_at) or now) <= now
    )

    failed_calls = sum(1 for call in recent_calls if call.outcome in {"failed", "dropped", "error"})
    error_rate_24h = _percentage(failed_calls, len(recent_calls))

    latency = calculate_percentiles(_turn_latency_samples(recent_calls)).to_dict()
    sheets_configured = bool(tenant.google_sheet_id) or bool(settings.google_sheet_id)
    sheets_status = (tenant.google_sheet_status or "disconnected").strip().lower()
    unsynced_calls = sum(1 for call in recent_calls if not call.sheet_synced)
    active_dids = _active_did_count(db, tenant_id)

    subsystems = [
        _subsystem(
            "database",
            "Database Pool",
            "operational" if db_state == "ok" and (db_latency_ms or 0) < 250 else "degraded" if db_state == "ok" else "down",
            latency_ms=db_latency_ms,
            detail="Pooled round-trip on the live request connection.",
        ),
        _subsystem(
            "llm",
            "LLM Turn Latency",
            "operational"
            if latency["p90_ms"] and latency["p90_ms"] <= settings.alert_p90_latency_ms_threshold
            else "degraded"
            if latency["p90_ms"]
            else "idle",
            latency_ms=latency["p50_ms"] or None,
            detail=f"{settings.llm_provider} · derived from {latency['sample_count']} persisted turn sample(s), no live provider call.",
        ),
        _subsystem(
            "telephony",
            "Telephony Ingress",
            "operational" if active_dids else "idle",
            detail=f"{active_dids} active inbound DID(s) via {settings.telephony_provider}.",
        ),
        _subsystem(
            "sheets_mirror",
            "Google Sheets Mirror",
            "operational"
            if sheets_status == "connected"
            else "degraded"
            if sheets_status == "error"
            else "not_configured"
            if not sheets_configured
            else "idle",
            detail=(
                f"{unsynced_calls} call(s) in the last 24h not yet mirrored."
                if sheets_status == "connected"
                else "No tenant spreadsheet is connected."
                if not sheets_configured
                else f"Mirror reported status '{sheets_status}'."
            ),
        ),
        _subsystem(
            "durable_jobs",
            "Durable Work Queue",
            "critical" if recent_dead_lettered or expired_leases else "degraded" if outbox_pending > 25 else "operational",
            detail=f"{outbox_pending} unpublished outbox event(s), {len(dead_lettered)} dead-lettered job(s) in total.",
        ),
    ]

    if any(item["status"] in {"down", "critical"} for item in subsystems) or error_rate_24h > 25:
        overall = HEALTH_CRITICAL
    elif any(item["status"] == "degraded" for item in subsystems) or error_rate_24h > settings.alert_error_rate_threshold:
        overall = HEALTH_DEGRADED
    else:
        overall = HEALTH_OPERATIONAL

    return {
        "tenant_id": tenant.id,
        "generated_at": now.isoformat(),
        "overall_status": overall,
        "db_pool_latency_ms": round(db_latency_ms, 2) if db_latency_ms is not None else None,
        "outbox_pending_count": outbox_pending,
        "outbox_oldest_pending_age_sec": outbox_lag_sec,
        "dead_lettered_recent_count": recent_dead_lettered,
        "dead_lettered_total_count": len(dead_lettered),
        "expired_lease_count": expired_leases,
        "sheets_mirror_status": sheets_status if sheets_configured else "not_configured",
        "sheets_mirror_configured": sheets_configured,
        "llm_provider": settings.llm_provider,
        "llm_p50_latency_ms": round(latency["p50_ms"]),
        "llm_p90_latency_ms": round(latency["p90_ms"]),
        "llm_sample_count": latency["sample_count"],
        "error_rate_24h": error_rate_24h,
        "calls_24h": len(recent_calls),
        "failed_calls_24h": failed_calls,
        "subsystems": subsystems,
    }


def _active_did_count(db: Session, tenant_id: str) -> int:
    return len(
        db.execute(
            select(TenantPhoneNumber.phone_number).where(
                TenantPhoneNumber.tenant_id == tenant_id,
                TenantPhoneNumber.active == 1,
            )
        )
        .scalars()
        .all()
    )


def _event(
    *,
    event_id: str,
    event_type: str,
    label: str,
    at: datetime | None,
    status: str,
    detail: str,
) -> dict[str, Any]:
    """Build one operational event with every free-text field scrubbed.

    ``scrub_value`` removes emails, phone numbers, and bounded string length, so
    an operator-authored note or a caller-supplied reason cannot leak a direct
    identifier into the feed.
    """

    return {
        "id": event_id,
        "event_type": event_type,
        "label": label,
        "occurred_at": _iso(at),
        "status": status,
        "detail": str(scrub_value(detail or "")),
    }


def get_recent_system_events(db: Session, tenant_id: str, limit: int = 20) -> dict[str, Any]:
    """Return a merged, PII-scrubbed stream of recent tenant operational events."""

    _require_tenant(db, tenant_id)
    capped = 20 if limit is None else max(1, min(int(limit), MAX_EVENT_LIMIT))
    now = _utcnow()
    window_start = now - timedelta(days=30)
    events: list[dict[str, Any]] = []

    calls = list(
        db.execute(
            select(Call)
            .where(Call.tenant_id == tenant_id, Call.started_at >= window_start)
            .order_by(Call.started_at.desc())
            .limit(capped)
        )
        .scalars()
        .all()
    )
    for call in calls:
        events.append(
            _event(
                event_id=f"call:{call.id}",
                event_type="call_completed",
                label="Call completed",
                at=call.ended_at or call.started_at,
                status="error" if _is_escalated(call) else "success" if _is_resolved(call) else "info",
                detail=f"{_bucket(call.intent, 'general')} · {call.duration_sec or 0}s · {_bucket(call.resolution_status, 'pending')}",
            )
        )
        if _is_escalated(call):
            events.append(
                _event(
                    event_id=f"escalation:{call.id}",
                    event_type="escalation_created",
                    label="Escalation created",
                    at=call.assigned_at or call.ended_at or call.started_at,
                    status="warning",
                    detail=f"priority {_bucket(call.escalation_priority, 'medium')} · status {_bucket(call.escalation_status, 'pending')}",
                )
            )

    worksheets = list(
        db.execute(
            select(WorksheetLog)
            .where(WorksheetLog.tenant_id == tenant_id, WorksheetLog.timestamp >= window_start)
            .order_by(WorksheetLog.timestamp.desc())
            .limit(capped)
        )
        .scalars()
        .all()
    )
    for row in worksheets:
        # row_data_json is deliberately never surfaced: it can hold order and
        # contact content mirrored from a caller conversation.
        events.append(
            _event(
                event_id=f"sheet:{row.id}",
                event_type="sheet_synced",
                label="Worksheet mirrored",
                at=row.timestamp,
                status="success",
                detail=f"{_bucket(row.worksheet_name, 'sheet')} · {_bucket(row.action_type, 'append')}",
            )
        )

    dids = list(
        db.execute(
            select(TenantPhoneNumber)
            .where(TenantPhoneNumber.tenant_id == tenant_id)
            .order_by(TenantPhoneNumber.created_at.desc())
            .limit(capped)
        )
        .scalars()
        .all()
    )
    for did in dids:
        # The E.164 number is a direct identifier, so even the event's own ID is
        # a short digest of it rather than the number itself.
        events.append(
            _event(
                event_id=f"did:{sha256(did.phone_number.encode('utf-8')).hexdigest()[:12]}",
                event_type="did_mapped",
                label="Inbound number mapped",
                at=did.created_at,
                status="success" if did.active else "info",
                detail=f"{_bucket(did.provider, 'provider')} · verification {_bucket(did.verification_mode, 'standard')}",
            )
        )

    jobs = list(
        db.execute(
            select(JobRun)
            .where(JobRun.tenant_id == tenant_id, JobRun.created_at >= window_start)
            .order_by(JobRun.updated_at.desc())
            .limit(capped)
        )
        .scalars()
        .all()
    )
    for job in jobs:
        if job.status not in {"dead_lettered", "succeeded", "cancelled"}:
            continue
        events.append(
            _event(
                event_id=f"job:{job.id}",
                event_type="job_settled",
                label="Durable job settled",
                at=job.finished_at or job.updated_at,
                status="error" if job.status == "dead_lettered" else "success" if job.status == "succeeded" else "warning",
                detail=f"{_bucket(job.job_type, 'job')} · attempt {job.attempt}/{job.max_attempts} · {_bucket(job.status)}",
            )
        )

    communications = list(
        db.execute(
            select(CommunicationLog)
            .where(CommunicationLog.tenant_id == tenant_id, CommunicationLog.timestamp >= window_start)
            .order_by(CommunicationLog.timestamp.desc())
            .limit(capped)
        )
        .scalars()
        .all()
    )
    for row in communications:
        # Recipient, subject, and body are all excluded by construction.
        events.append(
            _event(
                event_id=f"comm:{row.id}",
                event_type="communication_logged",
                label="Outbound communication",
                at=row.timestamp,
                status="error" if row.status == "failed" else "success",
                detail=f"{_bucket(row.channel, 'channel')} · {_bucket(row.status, 'sent')}",
            )
        )

    events.sort(key=lambda item: item["occurred_at"] or "", reverse=True)
    return {
        "tenant_id": tenant_id,
        "generated_at": now.isoformat(),
        "limit": capped,
        "events": events[:capped],
    }
