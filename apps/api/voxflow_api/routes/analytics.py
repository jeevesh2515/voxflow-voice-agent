"""Tenant-safe analytics, monitoring, and enterprise reporting endpoints."""

from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime, timedelta, timezone
from io import StringIO
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from ..auth import get_auth
from ..config import get_settings
from ..db import (
    Call,
    CampaignPolicyDecision,
    CampaignQueue,
    JobOutbox,
    JobRun,
    OutboundCampaign,
    Tenant,
    session_scope,
)
from ..jobs.staging import campaign_activation_mode, canary_tenant_ids, durable_campaign_dry_run

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


MAX_REPORT_DAYS = 90


def _tenant_id(request: Request, query_tenant: str | None = None) -> str:
    """Prefer authenticated tenant identity while preserving development compatibility."""
    auth = get_auth(request)
    if auth.tenant_id:
        return auth.tenant_id
    if query_tenant:
        return query_tenant
    return get_settings().default_tenant_id


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _seconds_since(value: datetime | None, now: datetime) -> int | None:
    utc_value = _as_utc(value)
    if utc_value is None:
        return None
    return max(0, int((now - utc_value).total_seconds()))


def _percentage(numerator: int, denominator: int) -> float:
    return round((numerator / denominator) * 100, 1) if denominator else 0.0


def _normalise_bucket(value: str | None, default: str = "unclassified") -> str:
    cleaned = (value or "").strip().lower().replace(" ", "_")
    return cleaned or default


def _add_alert(alerts: list[dict[str, str]], level: str, code: str, message: str) -> None:
    alerts.append({"level": level, "code": code, "message": message})


def _analytics_payload(tenant_id: str, days: int) -> dict[str, Any]:
    now = _utcnow()
    period_start = now - timedelta(days=days - 1)
    alert_rows: list[dict[str, str]] = []

    with session_scope() as db:
        tenant = db.get(Tenant, tenant_id)
        if tenant is None:
            raise HTTPException(status_code=404, detail="tenant_not_found")

        calls = (
            db.execute(
                select(Call).where(
                    Call.tenant_id == tenant_id,
                    Call.started_at >= period_start,
                )
            )
            .scalars()
            .all()
        )
        campaigns = db.execute(select(OutboundCampaign).where(OutboundCampaign.tenant_id == tenant_id)).scalars().all()
        queue_items = db.execute(select(CampaignQueue).where(CampaignQueue.tenant_id == tenant_id)).scalars().all()
        jobs = db.execute(select(JobRun).where(JobRun.tenant_id == tenant_id)).scalars().all()
        outbox = db.execute(select(JobOutbox).where(JobOutbox.tenant_id == tenant_id)).scalars().all()
        policy_decisions = (
            db.execute(
                select(CampaignPolicyDecision).where(
                    CampaignPolicyDecision.tenant_id == tenant_id,
                    CampaignPolicyDecision.created_at >= period_start,
                )
            )
            .scalars()
            .all()
        )

    total_calls = len(calls)
    resolved_calls = sum(1 for call in calls if call.resolution_status == "resolved" or call.outcome == "completed")
    escalated_calls = sum(1 for call in calls if call.escalated or call.outcome == "escalated")
    follow_up_open = sum(1 for call in calls if call.follow_up_required and call.staff_resolved_at is None)
    total_duration = sum(call.duration_sec or 0 for call in calls)
    verified_calls = sum(1 for call in calls if call.verified)

    daily: dict[str, dict[str, int]] = {}
    for offset in range(days):
        bucket_day = (period_start + timedelta(days=offset)).date().isoformat()
        daily[bucket_day] = {
            "date": bucket_day,
            "calls": 0,
            "resolved": 0,
            "escalated": 0,
            "duration_sec": 0,
        }
    for call in calls:
        started = _as_utc(call.started_at)
        if started is None:
            continue
        bucket = daily.get(started.date().isoformat())
        if bucket is None:
            continue
        bucket["calls"] += 1
        bucket["duration_sec"] += call.duration_sec or 0
        if call.resolution_status == "resolved" or call.outcome == "completed":
            bucket["resolved"] += 1
        if call.escalated or call.outcome == "escalated":
            bucket["escalated"] += 1

    intent_counts = Counter(_normalise_bucket(call.intent, "general") for call in calls)
    outcome_counts = Counter(_normalise_bucket(call.outcome, "unknown") for call in calls)
    satisfaction_counts = Counter(_normalise_bucket(call.satisfaction, "not_scored") for call in calls)
    language_counts = Counter(_normalise_bucket(call.language, "unknown") for call in calls)
    policy_counts = Counter(_normalise_bucket(decision.decision) for decision in policy_decisions)
    policy_reason_counts = Counter(_normalise_bucket(decision.reason_code) for decision in policy_decisions)
    queue_counts = Counter(_normalise_bucket(item.status, "queued") for item in queue_items)
    job_counts = Counter(_normalise_bucket(job.status, "ready") for job in jobs)

    active_jobs = [job for job in jobs if job.status in {"ready", "retry_scheduled", "running"}]
    ready_jobs = [job for job in jobs if job.status in {"ready", "retry_scheduled"}]
    oldest_ready = min((_as_utc(job.next_run_at or job.scheduled_at) for job in ready_jobs), default=None)
    oldest_outbox = min((_as_utc(item.created_at) for item in outbox if item.published_at is None), default=None)
    expired_leases = sum(
        1
        for job in jobs
        if job.status == "running" and job.lease_expires_at is not None and _as_utc(job.lease_expires_at) <= now
    )
    dead_letters = job_counts.get("dead_lettered", 0)
    unpublished_outbox = sum(1 for item in outbox if item.published_at is None)
    job_failure_count = sum(1 for job in jobs if job.status == "dead_lettered" or job.last_error_code)

    oldest_ready_age = _seconds_since(oldest_ready, now)
    oldest_outbox_age = _seconds_since(oldest_outbox, now)
    if expired_leases:
        _add_alert(alert_rows, "critical", "expired_worker_lease", f"{expired_leases} durable job lease(s) have expired.")
    if dead_letters:
        _add_alert(alert_rows, "critical", "dead_lettered_jobs", f"{dead_letters} job(s) require operator review.")
    if oldest_outbox_age is not None and oldest_outbox_age > 900:
        _add_alert(alert_rows, "warning", "outbox_publish_lag", "The oldest unpublished outbox event is older than 15 minutes.")
    if oldest_ready_age is not None and oldest_ready_age > 900:
        _add_alert(alert_rows, "warning", "job_backlog_age", "The oldest ready/retry job is older than 15 minutes.")
    if follow_up_open:
        _add_alert(alert_rows, "warning", "open_follow_ups", f"{follow_up_open} call follow-up item(s) remain unresolved.")
    if campaign_activation_mode() == "staged":
        _add_alert(alert_rows, "info", "campaigns_staged", "Campaign dispatch remains safely staged; no provider worker is active.")

    if any(alert["level"] == "critical" for alert in alert_rows):
        monitoring_state = "critical"
    elif any(alert["level"] == "warning" for alert in alert_rows):
        monitoring_state = "attention"
    else:
        monitoring_state = "healthy"

    return {
        "tenant": {
            "id": tenant.id,
            "name": tenant.name,
            "plan": tenant.plan,
        },
        "period": {
            "days": days,
            "from": period_start.date().isoformat(),
            "to": now.date().isoformat(),
            "generated_at": now.isoformat(),
        },
        "kpis": {
            "total_calls": total_calls,
            "resolved_calls": resolved_calls,
            "resolution_rate": _percentage(resolved_calls, total_calls),
            "escalated_calls": escalated_calls,
            "escalation_rate": _percentage(escalated_calls, total_calls),
            "open_follow_ups": follow_up_open,
            "verified_call_rate": _percentage(verified_calls, total_calls),
            "average_handle_time_sec": round(total_duration / total_calls) if total_calls else 0,
            "total_duration_sec": total_duration,
            "total_minutes": round(total_duration / 60, 2),
        },
        "trends": list(daily.values()),
        "distribution": {
            "intents": dict(sorted(intent_counts.items())),
            "outcomes": dict(sorted(outcome_counts.items())),
            "satisfaction": dict(sorted(satisfaction_counts.items())),
            "languages": dict(sorted(language_counts.items())),
        },
        "campaigns": {
            "total_campaigns": len(campaigns),
            "status_counts": dict(sorted(Counter(_normalise_bucket(campaign.status, "draft") for campaign in campaigns).items())),
            "target_status_counts": dict(sorted(queue_counts.items())),
            "policy_decision_counts": dict(sorted(policy_counts.items())),
            "policy_reason_counts": dict(sorted(policy_reason_counts.items())),
        },
        "monitoring": {
            "state": monitoring_state,
            "alerts": alert_rows,
            "job_status_counts": dict(sorted(job_counts.items())),
            "active_jobs": len(active_jobs),
            "expired_leases": expired_leases,
            "dead_lettered_jobs": dead_letters,
            "jobs_with_error_evidence": job_failure_count,
            "oldest_ready_age_sec": oldest_ready_age,
            "unpublished_outbox": unpublished_outbox,
            "oldest_outbox_age_sec": oldest_outbox_age,
            "rollout": {
                "activation_mode": campaign_activation_mode(),
                "canary_allowed": tenant_id in canary_tenant_ids(),
                "dry_run": durable_campaign_dry_run(),
            },
        },
    }


@router.get("/overview")
def analytics_overview(
    request: Request,
    tenant_id: str | None = Query(default=None, min_length=1),
    days: int = Query(30, ge=1, le=MAX_REPORT_DAYS),
) -> dict[str, Any]:
    """Return tenant-safe operational analytics and pull-based monitoring data."""
    return _analytics_payload(_tenant_id(request, tenant_id), days)


def _safe_csv_value(value: Any) -> Any:
    """Prevent spreadsheet formula execution when values are opened in a CSV client."""
    if isinstance(value, str) and value[:1] in {"=", "+", "-", "@"}:
        return f"'{value}"
    return value


@router.get("/report.csv")
def analytics_report_csv(
    request: Request,
    tenant_id: str | None = Query(default=None, min_length=1),
    days: int = Query(30, ge=1, le=MAX_REPORT_DAYS),
) -> StreamingResponse:
    """Export a tenant-only enterprise operations report without raw transcript data."""
    payload = _analytics_payload(_tenant_id(request, tenant_id), days)
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["VoxFlow Enterprise Operations Report"])
    writer.writerow(["Tenant", _safe_csv_value(payload["tenant"]["name"])])
    writer.writerow(["Tenant ID", _safe_csv_value(payload["tenant"]["id"])])
    writer.writerow(["Period", f'{payload["period"]["from"]} to {payload["period"]["to"]}'])
    writer.writerow(["Generated at", payload["period"]["generated_at"]])
    writer.writerow([])
    writer.writerow(["Metric", "Value"])
    for key, value in payload["kpis"].items():
        writer.writerow([key, _safe_csv_value(value)])
    writer.writerow([])
    writer.writerow(["Date", "Calls", "Resolved", "Escalated", "Duration seconds"])
    for point in payload["trends"]:
        writer.writerow([point["date"], point["calls"], point["resolved"], point["escalated"], point["duration_sec"]])
    writer.writerow([])
    writer.writerow(["Monitoring state", payload["monitoring"]["state"]])
    writer.writerow(["Alert level", "Code", "Message"])
    for alert in payload["monitoring"]["alerts"]:
        writer.writerow([alert["level"], alert["code"], _safe_csv_value(alert["message"])])

    filename = f'voxflow-{payload["tenant"]["id"]}-operations-report-{payload["period"]["to"]}.csv'
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
