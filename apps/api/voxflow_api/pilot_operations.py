"""Day 36 evidence-led controlled-pilot operations service.

This module deliberately exposes observability and trusted-service evidence
persistence, not an operational control plane. It never starts a worker,
registers a provider callback, sends an integration request, or expands a
cohort. HTTP routes built on it are read-only.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any
import uuid
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from .config import get_settings
from .db import (
    JobRun,
    PilotConfiguration,
    PilotOperationalEvidence,
    ProviderCallbackAdapterAudit,
    ProviderEvent,
    SideEffectIntent,
)
from .jobs.staging import (
    durable_campaign_dry_run,
    durable_campaign_worker_enabled,
    durable_side_effects_dry_run,
    durable_side_effects_worker_enabled,
)


EVIDENCE_DECISIONS: dict[str, set[str]] = {
    "preflight": {"continue_same_cohort", "blocked"},
    "hold_point": {"continue_same_cohort", "pause", "rollback_requested", "blocked"},
    "pause": {"pause"},
    "rollback": {"rollback_requested", "blocked"},
}


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _safe_local_day(value: datetime, timezone_name: str) -> str:
    try:
        return _utc(value).astimezone(ZoneInfo(timezone_name)).date().isoformat()  # type: ignore[union-attr]
    except Exception:
        return _utc(value).date().isoformat()  # type: ignore[union-attr]


def _config(db: Session, tenant_id: str) -> PilotConfiguration | None:
    return db.get(PilotConfiguration, tenant_id)


def _latest_evidence(
    db: Session,
    *,
    config: PilotConfiguration,
) -> PilotOperationalEvidence | None:
    return (
        db.query(PilotOperationalEvidence)
        .filter(
            PilotOperationalEvidence.tenant_id == config.tenant_id,
            PilotOperationalEvidence.pilot_id == config.pilot_id,
            PilotOperationalEvidence.pilot_version == config.version,
        )
        .order_by(PilotOperationalEvidence.created_at.desc())
        .first()
    )


def _evidence_summary(evidence: PilotOperationalEvidence | None) -> dict[str, object] | None:
    if evidence is None:
        return None
    return {
        "evidence_kind": evidence.evidence_kind,
        "evidence_key": evidence.evidence_key,
        "decision": evidence.decision,
        "reason_code": evidence.reason_code,
        "recorded_by": evidence.recorded_by,
        "created_at": _utc(evidence.created_at).isoformat(),
    }


def _queue_snapshot(db: Session, *, tenant_id: str, now: datetime) -> dict[str, int]:
    jobs = db.query(JobRun).filter(JobRun.tenant_id == tenant_id).all()
    campaign_jobs = [job for job in jobs if job.job_type == "campaign.target.dispatch"]
    running = [job for job in campaign_jobs if job.status == "running"]
    expired_leases = [
        job
        for job in running
        if _utc(job.lease_expires_at) is not None and _utc(job.lease_expires_at) < now
    ]
    return {
        "campaign_ready_or_retrying": sum(job.status in {"ready", "retry_scheduled"} for job in campaign_jobs),
        "campaign_running": len(running),
        "campaign_dead_lettered": sum(job.status == "dead_letter" for job in campaign_jobs),
        "campaign_expired_leases": len(expired_leases),
        "all_tenant_running": sum(job.status == "running" for job in jobs),
    }


def _callback_snapshot(db: Session, *, tenant_id: str) -> dict[str, int]:
    audits = db.query(ProviderCallbackAdapterAudit).filter(ProviderCallbackAdapterAudit.tenant_id == tenant_id).all()
    events = db.query(ProviderEvent).filter(ProviderEvent.tenant_id == tenant_id).all()
    return {
        "signed_callback_events": len(events),
        "callback_anomalies": sum(bool(event.anomaly_code) for event in events),
        "adapter_audits": len(audits),
        "adapter_verification_failures": sum(audit.verification_status != "verified" for audit in audits),
        "adapter_blocked_applications": sum(audit.application_status != "applied" for audit in audits),
    }


def _side_effect_snapshot(db: Session, *, tenant_id: str) -> dict[str, int]:
    intents = db.query(SideEffectIntent).filter(SideEffectIntent.tenant_id == tenant_id).all()
    return {
        "intent_count": len(intents),
        "pending_count": sum(intent.status in {"queued", "running", "retry_scheduled"} for intent in intents),
        "error_count": sum(intent.status in {"failed", "dead_letter"} for intent in intents),
    }


def operational_preflight(db: Session, *, tenant_id: str, now: datetime | None = None) -> dict[str, Any]:
    """Build a redacted Day 36 preflight packet with explicit hard stops."""

    now = _utc(now or datetime.now(timezone.utc))
    config = _config(db, tenant_id)
    if config is None:
        return {
            "tenant_id": tenant_id,
            "configured": False,
            "preflight": {
                "state": "blocked",
                "blocking_reasons": ["pilot_configuration_missing"],
                "no_auto_expansion": True,
                "requires_human_hold_point": True,
            },
            "queue": _queue_snapshot(db, tenant_id=tenant_id, now=now),
            "callbacks": _callback_snapshot(db, tenant_id=tenant_id),
            "side_effects": _side_effect_snapshot(db, tenant_id=tenant_id),
            "latest_evidence": None,
        }

    queue = _queue_snapshot(db, tenant_id=tenant_id, now=now)
    callbacks = _callback_snapshot(db, tenant_id=tenant_id)
    side_effects = _side_effect_snapshot(db, tenant_id=tenant_id)
    settings = get_settings()
    blocking_reasons: list[str] = []
    if tenant_id not in settings.pilot_readiness_approved_tenant_ids:
        blocking_reasons.append("pilot_tenant_not_environment_approved")
    if config.status != "approved":
        blocking_reasons.append(f"pilot_status_{config.status}")
    if _utc(config.expires_at) is None or _utc(config.expires_at) <= now:
        blocking_reasons.append("pilot_expired")
    if not config.primary_escalation_owner or not config.backup_escalation_owner or not config.approved_by:
        blocking_reasons.append("pilot_human_approval_or_coverage_missing")
    if durable_campaign_worker_enabled() or durable_side_effects_worker_enabled():
        blocking_reasons.append("worker_must_remain_disabled_for_evidence_review")
    if not durable_campaign_dry_run() or not durable_side_effects_dry_run():
        blocking_reasons.append("dry_run_must_remain_enabled_for_evidence_review")
    if queue["campaign_running"] or queue["campaign_expired_leases"]:
        blocking_reasons.append("campaign_queue_claim_requires_manual_review")
    if queue["campaign_dead_lettered"]:
        blocking_reasons.append("campaign_dead_letter_requires_disposition")
    if callbacks["callback_anomalies"] or callbacks["adapter_verification_failures"]:
        blocking_reasons.append("callback_integrity_requires_review")
    if side_effects["error_count"]:
        blocking_reasons.append("side_effect_error_requires_review")

    latest = _latest_evidence(db, config=config)
    return {
        "tenant_id": tenant_id,
        "configured": True,
        "pilot": {
            "pilot_id": config.pilot_id,
            "version": config.version,
            "status": config.status,
            "cohort_id": config.cohort_id,
            "cohort_size": config.cohort_size,
            "timezone_name": config.timezone_name,
            "calling_window_start": config.calling_window_start,
            "calling_window_end": config.calling_window_end,
            "expires_at": _utc(config.expires_at).isoformat(),
            "metric_contract_version": config.metric_contract_version,
        },
        "preflight": {
            "state": "review_required" if not blocking_reasons else "blocked",
            "blocking_reasons": blocking_reasons,
            "no_auto_expansion": True,
            "requires_human_hold_point": True,
            "current_local_operating_day": _safe_local_day(now, config.timezone_name),
        },
        "workers": {
            "campaign_worker_enabled": durable_campaign_worker_enabled(),
            "campaign_dry_run": durable_campaign_dry_run(),
            "side_effect_worker_enabled": durable_side_effects_worker_enabled(),
            "side_effect_dry_run": durable_side_effects_dry_run(),
        },
        "queue": queue,
        "callbacks": callbacks,
        "side_effects": side_effects,
        "latest_evidence": _evidence_summary(latest),
    }


def hold_point_scorecard(db: Session, *, tenant_id: str, now: datetime | None = None) -> dict[str, Any]:
    """Return the current same-cohort hold-point state without changing it."""

    now = _utc(now or datetime.now(timezone.utc))
    preflight = operational_preflight(db, tenant_id=tenant_id, now=now)
    if not preflight["configured"]:
        return {
            **preflight,
            "hold_point": {
                "state": "blocked",
                "decision": None,
                "reason": "pilot_configuration_missing",
                "fresh_for_current_operating_day": False,
                "expansion_permitted": False,
            },
        }

    config = _config(db, tenant_id)
    assert config is not None
    latest = _latest_evidence(db, config=config)
    latest_local_day = _safe_local_day(_utc(latest.created_at), config.timezone_name) if latest else None
    fresh = bool(latest and latest_local_day == _safe_local_day(now, config.timezone_name))
    decision = latest.decision if latest else None
    state = "blocked"
    reason = "hold_point_evidence_missing"
    if preflight["preflight"]["blocking_reasons"]:
        reason = "preflight_blocked"
    elif latest and not fresh:
        reason = "hold_point_evidence_not_current"
    elif latest and decision != "continue_same_cohort":
        reason = f"hold_point_{decision}"
    elif latest and fresh:
        state = "reviewed_same_cohort"
        reason = "human_review_recorded"

    return {
        **preflight,
        "hold_point": {
            "state": state,
            "decision": decision,
            "reason": reason,
            "fresh_for_current_operating_day": fresh,
            "expansion_permitted": False,
            "same_cohort_only": True,
            "latest_evidence": _evidence_summary(latest),
        },
    }


def record_operational_evidence(
    db: Session,
    *,
    tenant_id: str,
    evidence_kind: str,
    evidence_key: str,
    decision: str,
    reason_code: str,
    recorded_by: str,
    now: datetime | None = None,
) -> dict[str, object]:
    """Persist a redacted operator decision from a trusted direct-service path.

    This is intentionally not exposed through HTTP. It cannot enable execution;
    it records a review decision and an immutable aggregate-only snapshot.
    """

    now = _utc(now or datetime.now(timezone.utc))
    config = _config(db, tenant_id)
    if config is None:
        raise ValueError("pilot configuration is missing")
    if evidence_kind not in EVIDENCE_DECISIONS:
        raise ValueError("unsupported evidence kind")
    if decision not in EVIDENCE_DECISIONS[evidence_kind]:
        raise ValueError("decision is not allowed for this evidence kind")
    if not evidence_key.strip() or not recorded_by.strip():
        raise ValueError("evidence_key and recorded_by are required")

    existing = (
        db.query(PilotOperationalEvidence)
        .filter(
            PilotOperationalEvidence.tenant_id == tenant_id,
            PilotOperationalEvidence.pilot_id == config.pilot_id,
            PilotOperationalEvidence.pilot_version == config.version,
            PilotOperationalEvidence.evidence_kind == evidence_kind,
            PilotOperationalEvidence.evidence_key == evidence_key.strip(),
        )
        .first()
    )
    if existing is not None:
        return {"id": existing.id, "created": False, "evidence": _evidence_summary(existing)}

    snapshot = operational_preflight(db, tenant_id=tenant_id, now=now)
    snapshot_json = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
    evidence = PilotOperationalEvidence(
        id=f"poe-{uuid.uuid4().hex[:20]}",
        tenant_id=tenant_id,
        pilot_id=config.pilot_id,
        pilot_version=config.version,
        evidence_kind=evidence_kind,
        evidence_key=evidence_key.strip(),
        decision=decision,
        reason_code=reason_code.strip()[:128],
        snapshot_json=snapshot_json,
        recorded_by=recorded_by.strip()[:128],
        created_at=now,
    )
    db.add(evidence)
    db.flush()
    return {
        "id": evidence.id,
        "created": True,
        "snapshot_hash": sha256(snapshot_json.encode("utf-8")).hexdigest(),
        "evidence": _evidence_summary(evidence),
    }


def pilot_operations_hold_allows_dispatch(
    db: Session,
    *,
    config: PilotConfiguration,
    now: datetime,
) -> tuple[bool, str, dict[str, object]]:
    """Return the final Day 36 same-cohort hold condition for policy admission."""

    if not get_settings().pilot_operations_evidence_enforced:
        return True, "pilot_operations_gate_test_bypass", {"enforced": False}
    latest = _latest_evidence(db, config=config)
    if latest is None:
        return False, "pilot_hold_point_evidence_missing", {"pilot_id": config.pilot_id}
    current_day = _safe_local_day(now, config.timezone_name)
    if _safe_local_day(_utc(latest.created_at), config.timezone_name) != current_day:
        return False, "pilot_hold_point_evidence_not_current", {"pilot_id": config.pilot_id}
    if latest.decision != "continue_same_cohort":
        return False, f"pilot_hold_point_{latest.decision}", {"pilot_id": config.pilot_id}
    if latest.evidence_kind not in {"preflight", "hold_point"}:
        return False, "pilot_hold_point_invalid_kind", {"pilot_id": config.pilot_id}
    return True, "pilot_hold_point_same_cohort_reviewed", {
        "pilot_id": config.pilot_id,
        "evidence_kind": latest.evidence_kind,
        "evidence_key": latest.evidence_key,
    }
