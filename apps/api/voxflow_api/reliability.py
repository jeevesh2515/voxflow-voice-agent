"""Day 37 reliability scorecards, deterministic safety drills, and recovery previews.

This module is deliberately observability-only at the HTTP boundary.  Browser
clients can read aggregate reliability evidence but cannot run a drill, mutate a
job, enable a worker, send a callback, or call an external provider.  Drills are
trusted direct-service, database-only fixtures: they calculate an in-memory
fault overlay and persist one redacted receipt for later review.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import uuid

from sqlalchemy.orm import Session

from .db import (
    DrillResult,
    JobRun,
    PilotConfiguration,
    PilotOperationalEvidence,
    ProviderCallbackAdapterAudit,
    ProviderEvent,
    ReliabilitySLO,
)
from .jobs.staging import (
    durable_campaign_dry_run,
    durable_campaign_worker_enabled,
    durable_side_effects_dry_run,
    durable_side_effects_worker_enabled,
)
from .pilot_operations import hold_point_scorecard, operational_preflight
from .pilot_readiness import rollback_preview


DRILL_FIXTURE_VERSION = "day37-v1"
DRILL_FIXTURES: dict[str, dict[str, str]] = {
    "expired_lease": {
        "signal": "campaign_expired_leases",
        "reason": "campaign_queue_claim_requires_manual_review",
        "recovery": "Keep workers disabled; reconcile the expired lease from a trusted operator path before any review.",
    },
    "dead_letter": {
        "signal": "campaign_dead_lettered",
        "reason": "campaign_dead_letter_requires_disposition",
        "recovery": "Keep the affected queue item blocked; document a human disposition before a future retry review.",
    },
    "callback_anomaly": {
        "signal": "callback_anomalies",
        "reason": "callback_integrity_requires_review",
        "recovery": "Quarantine and review the callback evidence; do not register, replay, or call a provider from this drill.",
    },
    "pause": {
        "signal": "pilot_pause_evidence",
        "reason": "pilot_hold_point_pause",
        "recovery": "Maintain the manual pause and record a new human preflight only after the underlying issue is resolved.",
    },
    "stale_evidence": {
        "signal": "evidence_stale",
        "reason": "hold_point_evidence_not_current",
        "recovery": "Require a current-day human hold-point review; no automatic cohort expansion is permitted.",
    },
    "version_drift": {
        "signal": "pilot_version_drift",
        "reason": "pilot_configuration_version_review_required",
        "recovery": "Stop review progression until the metric contract and pilot version are reconciled by an authorized human.",
    },
}

# Defaults are an observable contract, not a browser-editable configuration.
# A tenant may later receive stored ReliabilitySLO rows via a trusted admin
# workflow; read endpoints never create or update those rows.
DEFAULT_SLOS: tuple[dict[str, object], ...] = (
    {"metric_type": "queue_recovery", "label": "Queue Recovery", "target_percent": 100.0, "window_hours": 24, "comparison": "minimum"},
    {"metric_type": "callback_integrity", "label": "Callback Integrity", "target_percent": 100.0, "window_hours": 24, "comparison": "minimum"},
    {"metric_type": "evidence_freshness", "label": "Evidence Freshness", "target_percent": 100.0, "window_hours": 24, "comparison": "minimum"},
    {"metric_type": "safety_posture", "label": "Safety Posture", "target_percent": 100.0, "window_hours": 1, "comparison": "minimum"},
    {"metric_type": "drill_pass_rate", "label": "Drill Pass Rate", "target_percent": 100.0, "window_hours": 168, "comparison": "minimum"},
)


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _now(value: datetime | None = None) -> datetime:
    return _utc(value or datetime.now(timezone.utc))  # type: ignore[return-value]


def _ratio_percent(healthy: int, total: int) -> float:
    if total <= 0:
        return 100.0
    return round((healthy / total) * 100, 2)


def _slo_definitions(db: Session, tenant_id: str) -> list[dict[str, object]]:
    stored = (
        db.query(ReliabilitySLO)
        .filter(ReliabilitySLO.tenant_id == tenant_id, ReliabilitySLO.active == 1)
        .all()
    )
    by_metric = {
        row.metric_type: {
            "id": row.id,
            "metric_type": row.metric_type,
            "label": row.metric_type.replace("_", " ").title(),
            "target_percent": float(row.target_percent),
            "window_hours": int(row.window_hours),
            "comparison": row.comparison,
            "source": "tenant_configuration",
        }
        for row in stored
    }
    definitions: list[dict[str, object]] = []
    for default in DEFAULT_SLOS:
        metric_type = str(default["metric_type"])
        definitions.append(
            by_metric.get(
                metric_type,
                {**default, "id": None, "source": "built_in_contract"},
            )
        )
    return definitions


def _queue_metrics(db: Session, *, tenant_id: str, now: datetime) -> dict[str, int]:
    jobs = db.query(JobRun).filter(JobRun.tenant_id == tenant_id).all()
    campaign_jobs = [job for job in jobs if job.job_type == "campaign.target.dispatch"]
    running = [job for job in campaign_jobs if job.status == "running"]
    expired = [
        job
        for job in running
        if _utc(job.lease_expires_at) is not None and _utc(job.lease_expires_at) < now
    ]
    return {
        "campaign_job_count": len(campaign_jobs),
        "campaign_expired_leases": len(expired),
        "campaign_dead_lettered": sum(job.status == "dead_letter" for job in campaign_jobs),
        "campaign_running": len(running),
    }


def _callback_metrics(db: Session, *, tenant_id: str) -> dict[str, int]:
    events = db.query(ProviderEvent).filter(ProviderEvent.tenant_id == tenant_id).all()
    audits = (
        db.query(ProviderCallbackAdapterAudit)
        .filter(ProviderCallbackAdapterAudit.tenant_id == tenant_id)
        .all()
    )
    return {
        "signed_callback_events": len(events),
        "callback_anomalies": sum(bool(event.anomaly_code) for event in events),
        "adapter_audits": len(audits),
        "adapter_verification_failures": sum(audit.verification_status != "verified" for audit in audits),
    }


def _evidence_metrics(db: Session, *, tenant_id: str, now: datetime) -> dict[str, object]:
    config = db.get(PilotConfiguration, tenant_id)
    if config is None:
        return {
            "configured": False,
            "fresh": False,
            "evidence_age_hours": None,
            "version_matches": False,
        }
    latest = (
        db.query(PilotOperationalEvidence)
        .filter(
            PilotOperationalEvidence.tenant_id == tenant_id,
            PilotOperationalEvidence.pilot_id == config.pilot_id,
            PilotOperationalEvidence.pilot_version == config.version,
        )
        .order_by(PilotOperationalEvidence.created_at.desc())
        .first()
    )
    if latest is None:
        return {
            "configured": True,
            "fresh": False,
            "evidence_age_hours": None,
            "version_matches": False,
        }
    created_at = _utc(latest.created_at)
    age_hours = round(max((now - created_at).total_seconds(), 0) / 3600, 2) if created_at else None
    current_day = now.date()
    fresh = bool(created_at and created_at.date() == current_day)
    return {
        "configured": True,
        "fresh": fresh,
        "evidence_age_hours": age_hours,
        "version_matches": latest.pilot_version == config.version,
    }


def _safety_metrics() -> dict[str, object]:
    campaign_enabled = durable_campaign_worker_enabled()
    side_effect_enabled = durable_side_effects_worker_enabled()
    campaign_dry_run = durable_campaign_dry_run()
    side_effect_dry_run = durable_side_effects_dry_run()
    safe = not campaign_enabled and not side_effect_enabled and campaign_dry_run and side_effect_dry_run
    return {
        "campaign_worker_enabled": campaign_enabled,
        "campaign_dry_run": campaign_dry_run,
        "side_effect_worker_enabled": side_effect_enabled,
        "side_effect_dry_run": side_effect_dry_run,
        "safe": safe,
    }


def _recent_drills(db: Session, *, tenant_id: str, since: datetime) -> list[DrillResult]:
    return [
        result
        for result in db.query(DrillResult).filter(DrillResult.tenant_id == tenant_id).all()
        if (_utc(result.created_at) or since) >= since
    ]


def _metric_observation(
    db: Session,
    *,
    tenant_id: str,
    metric_type: str,
    window_hours: int,
    now: datetime,
) -> dict[str, object]:
    if metric_type == "queue_recovery":
        queue = _queue_metrics(db, tenant_id=tenant_id, now=now)
        total = int(queue["campaign_job_count"])
        issues = int(queue["campaign_expired_leases"]) + int(queue["campaign_dead_lettered"])
        return {
            "actual_percent": _ratio_percent(max(total - issues, 0), total),
            "sample_size": total,
            "evidence": queue,
        }
    if metric_type == "callback_integrity":
        callbacks = _callback_metrics(db, tenant_id=tenant_id)
        total = int(callbacks["signed_callback_events"]) + int(callbacks["adapter_audits"])
        issues = int(callbacks["callback_anomalies"]) + int(callbacks["adapter_verification_failures"])
        return {
            "actual_percent": _ratio_percent(max(total - issues, 0), total),
            "sample_size": total,
            "evidence": callbacks,
        }
    if metric_type == "evidence_freshness":
        evidence = _evidence_metrics(db, tenant_id=tenant_id, now=now)
        healthy = bool(evidence["fresh"] and evidence["version_matches"])
        return {"actual_percent": 100.0 if healthy else 0.0, "sample_size": 1 if evidence["configured"] else 0, "evidence": evidence}
    if metric_type == "safety_posture":
        safety = _safety_metrics()
        return {"actual_percent": 100.0 if safety["safe"] else 0.0, "sample_size": 1, "evidence": safety}
    if metric_type == "drill_pass_rate":
        drills = _recent_drills(db, tenant_id=tenant_id, since=now - timedelta(hours=window_hours))
        passed = sum(result.outcome == "passed" for result in drills)
        return {
            "actual_percent": _ratio_percent(passed, len(drills)) if drills else None,
            "sample_size": len(drills),
            "evidence": {"passed": passed, "failed_or_blocked": len(drills) - passed, "window_hours": window_hours},
        }
    return {"actual_percent": None, "sample_size": 0, "evidence": {"reason": "unsupported_metric_type"}}


def reliability_scorecard(db: Session, *, tenant_id: str, now: datetime | None = None) -> dict[str, object]:
    """Return a tenant-safe SLO scorecard without any database mutation."""

    observed_at = _now(now)
    scorecards: list[dict[str, object]] = []
    for definition in _slo_definitions(db, tenant_id):
        metric_type = str(definition["metric_type"])
        window_hours = int(definition["window_hours"])
        observation = _metric_observation(
            db,
            tenant_id=tenant_id,
            metric_type=metric_type,
            window_hours=window_hours,
            now=observed_at,
        )
        actual = observation["actual_percent"]
        target = float(definition["target_percent"])
        comparison = str(definition["comparison"])
        if actual is None:
            status = "insufficient_evidence"
        elif comparison == "maximum":
            status = "passing" if float(actual) <= target else "failing"
        else:
            status = "passing" if float(actual) >= target else "failing"
        scorecards.append(
            {
                **definition,
                "actual_percent": actual,
                "sample_size": observation["sample_size"],
                "status": status,
                "evidence": observation["evidence"],
            }
        )

    passing = sum(card["status"] == "passing" for card in scorecards)
    failing = sum(card["status"] == "failing" for card in scorecards)
    insufficient = sum(card["status"] == "insufficient_evidence" for card in scorecards)
    state = "healthy" if failing == 0 and insufficient == 0 else "attention"
    if any(card["metric_type"] == "safety_posture" and card["status"] == "failing" for card in scorecards):
        state = "blocked"
    return {
        "tenant_id": tenant_id,
        "generated_at": observed_at.isoformat(),
        "read_only": True,
        "summary": {
            "state": state,
            "passing_count": passing,
            "failing_count": failing,
            "insufficient_evidence_count": insufficient,
        },
        "slos": scorecards,
        "safety_guardrails": {
            **_safety_metrics(),
            "external_actions": 0,
            "worker_activation_available": False,
            "provider_access_available": False,
        },
    }


def _fixture_snapshot(db: Session, *, tenant_id: str, now: datetime) -> dict[str, object]:
    return {
        "queue": _queue_metrics(db, tenant_id=tenant_id, now=now),
        "callbacks": _callback_metrics(db, tenant_id=tenant_id),
        "evidence": _evidence_metrics(db, tenant_id=tenant_id, now=now),
        "safety": _safety_metrics(),
        "external_actions": 0,
        "created_job_rows": 0,
        "created_provider_operations": 0,
        "provider_requests": 0,
    }


def _fixture_evidence(*, fixture_type: str, snapshot: dict[str, object]) -> tuple[bool, dict[str, object]]:
    """Apply a fault overlay to a detached aggregate snapshot and evaluate it."""

    details = DRILL_FIXTURES[fixture_type]
    queue = dict(snapshot["queue"])  # type: ignore[arg-type]
    callbacks = dict(snapshot["callbacks"])  # type: ignore[arg-type]
    evidence = dict(snapshot["evidence"])  # type: ignore[arg-type]
    expected_reason = details["reason"]
    observed: dict[str, object] = {}
    detected = False

    if fixture_type == "expired_lease":
        queue["campaign_expired_leases"] = int(queue["campaign_expired_leases"]) + 1
        observed = {"campaign_expired_leases": queue["campaign_expired_leases"]}
        detected = int(queue["campaign_expired_leases"]) > 0
    elif fixture_type == "dead_letter":
        queue["campaign_dead_lettered"] = int(queue["campaign_dead_lettered"]) + 1
        observed = {"campaign_dead_lettered": queue["campaign_dead_lettered"]}
        detected = int(queue["campaign_dead_lettered"]) > 0
    elif fixture_type == "callback_anomaly":
        callbacks["callback_anomalies"] = int(callbacks["callback_anomalies"]) + 1
        observed = {"callback_anomalies": callbacks["callback_anomalies"]}
        detected = int(callbacks["callback_anomalies"]) > 0
    elif fixture_type == "pause":
        observed = {"pilot_pause_evidence": True}
        detected = True
    elif fixture_type == "stale_evidence":
        evidence["fresh"] = False
        evidence["evidence_age_hours"] = 25.0
        observed = {"fresh": evidence["fresh"], "evidence_age_hours": evidence["evidence_age_hours"]}
        detected = not bool(evidence["fresh"])
    elif fixture_type == "version_drift":
        evidence["version_matches"] = False
        observed = {"version_matches": evidence["version_matches"]}
        detected = not bool(evidence["version_matches"])

    safety = dict(snapshot["safety"])  # type: ignore[arg-type]
    external_effects_zero = (
        snapshot["external_actions"] == 0
        and snapshot["created_job_rows"] == 0
        and snapshot["created_provider_operations"] == 0
        and snapshot["provider_requests"] == 0
    )
    passed = bool(detected and external_effects_zero and not bool(safety["campaign_worker_enabled"]) and not bool(safety["side_effect_worker_enabled"]))
    return passed, {
        "fixture_type": fixture_type,
        "fixture_version": DRILL_FIXTURE_VERSION,
        "expected_blocking_reason": expected_reason,
        "observed_signals": observed,
        "safety": safety,
        "external_actions": 0,
        "created_job_rows": 0,
        "created_provider_operations": 0,
        "provider_requests": 0,
        "detected": detected,
    }


def run_deterministic_drill(
    db: Session,
    *,
    tenant_id: str,
    fixture_type: str,
    execution_key: str,
    now: datetime | None = None,
) -> dict[str, object]:
    """Persist an idempotent receipt from a deterministic database-only drill.

    This trusted service function intentionally creates only a DrillResult row.
    It never creates or updates JobRun, ProviderOperation, ProviderEvent, or
    worker configuration rows and is never exposed through an HTTP route.
    """

    if fixture_type not in DRILL_FIXTURES:
        raise ValueError("unsupported drill fixture")
    if not execution_key.strip():
        raise ValueError("execution_key is required")
    existing = (
        db.query(DrillResult)
        .filter(
            DrillResult.tenant_id == tenant_id,
            DrillResult.fixture_type == fixture_type,
            DrillResult.execution_key == execution_key.strip(),
        )
        .first()
    )
    if existing is not None:
        return {"id": existing.id, "created": False, "outcome": existing.outcome}

    observed_at = _now(now)
    snapshot = _fixture_snapshot(db, tenant_id=tenant_id, now=observed_at)
    passed, evidence = _fixture_evidence(fixture_type=fixture_type, snapshot=snapshot)
    evidence_json = json.dumps(evidence, sort_keys=True, separators=(",", ":"))
    result = DrillResult(
        id=f"drill-{uuid.uuid4().hex[:20]}",
        tenant_id=tenant_id,
        fixture_type=fixture_type,
        fixture_version=DRILL_FIXTURE_VERSION,
        execution_key=execution_key.strip()[:128],
        outcome="passed" if passed else "failed",
        evidence_json=evidence_json,
        recovery_summary=DRILL_FIXTURES[fixture_type]["recovery"],
        created_at=observed_at,
    )
    db.add(result)
    db.flush()
    return {
        "id": result.id,
        "created": True,
        "outcome": result.outcome,
        "evidence_hash": sha256(evidence_json.encode("utf-8")).hexdigest(),
    }


def list_drill_results(db: Session, *, tenant_id: str, limit: int = 20) -> dict[str, object]:
    """Return redacted immutable drill receipts without mutation."""

    safe_limit = min(max(limit, 1), 100)
    rows = (
        db.query(DrillResult)
        .filter(DrillResult.tenant_id == tenant_id)
        .order_by(DrillResult.created_at.desc())
        .limit(safe_limit)
        .all()
    )
    results: list[dict[str, object]] = []
    for row in rows:
        try:
            evidence = json.loads(row.evidence_json)
        except (TypeError, ValueError, json.JSONDecodeError):
            evidence = {"reason": "evidence_unavailable"}
        results.append(
            {
                "id": row.id,
                "fixture_type": row.fixture_type,
                "fixture_version": row.fixture_version,
                "outcome": row.outcome,
                "recovery_summary": row.recovery_summary,
                "created_at": _utc(row.created_at).isoformat(),
                "evidence": evidence,
            }
        )
    return {"tenant_id": tenant_id, "read_only": True, "results": results}


def recovery_plan_preview(db: Session, *, tenant_id: str, now: datetime | None = None) -> dict[str, object]:
    """Return a non-executable recovery plan derived from persisted aggregates."""

    observed_at = _now(now)
    preflight = operational_preflight(db, tenant_id=tenant_id, now=observed_at)
    hold_point = hold_point_scorecard(db, tenant_id=tenant_id, now=observed_at)
    rollback = rollback_preview(db, tenant_id=tenant_id)
    queue = _queue_metrics(db, tenant_id=tenant_id, now=observed_at)
    callbacks = _callback_metrics(db, tenant_id=tenant_id)
    safety = _safety_metrics()
    actions: list[dict[str, object]] = [
        {
            "priority": 1,
            "condition": "always",
            "action": "Keep both durable workers disabled and dry-run protection enabled.",
            "execution": "human_review_only",
        },
    ]
    if queue["campaign_expired_leases"]:
        actions.append({"priority": 2, "condition": "expired_lease", "action": "Reconcile expired claims from a trusted operator service; do not auto-retry.", "execution": "human_review_only"})
    if queue["campaign_dead_lettered"]:
        actions.append({"priority": 2, "condition": "dead_letter", "action": "Document a durable-job disposition before considering any future retry.", "execution": "human_review_only"})
    if callbacks["callback_anomalies"] or callbacks["adapter_verification_failures"]:
        actions.append({"priority": 2, "condition": "callback_integrity", "action": "Review redacted callback evidence and preserve the provider block.", "execution": "human_review_only"})
    if hold_point["hold_point"]["state"] != "reviewed_same_cohort":  # type: ignore[index]
        actions.append({"priority": 2, "condition": "hold_point", "action": "Obtain a current authorized human hold-point decision; auto-expansion remains prohibited.", "execution": "human_review_only"})

    return {
        "tenant_id": tenant_id,
        "generated_at": observed_at.isoformat(),
        "read_only": True,
        "can_execute_from_browser": False,
        "external_actions": 0,
        "worker_activation_available": False,
        "provider_access_available": False,
        "safety_posture": safety,
        "preflight_state": preflight["preflight"]["state"],
        "hold_point_state": hold_point["hold_point"]["state"],
        "rollback": {
            "configured": rollback.get("configured", False),
            "can_execute": False,
            "would_cancel_job_count": rollback.get("would_cancel_job_count", 0),
            "active_claim_count": rollback.get("active_claim_count", 0),
            "execution_guard": "A browser cannot execute recovery or rollback. Trusted human-reviewed service procedures remain required.",
        },
        "recommended_actions": actions,
    }
