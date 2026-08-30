"""Day 51 tenant alert threshold evaluation and dispatch intent.

Evaluation is pure and read-only: it turns persisted KPI/health aggregates into
a list of triggered alerts. Dispatch deliberately does **not** send mail or POST
a webhook inline — it enqueues one typed ``notification.dispatch`` side-effect
intent in the same transaction, which the separately deployed, feature-gated
worker owns. An API request can therefore never block on SMTP, leak a customer
email into a request trace, or turn a browser poll into outbound traffic.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import AgentState, Tenant
from ..jobs.side_effects import NOTIFICATION_DISPATCH, enqueue_side_effect


# Thresholds live in the existing tenant-scoped AgentState key/value ledger so a
# tenant can be tuned without a schema migration. Unknown keys are ignored.
THRESHOLD_STATE_KEY_PREFIX = "observability.alert_thresholds"

SEVERITY_CRITICAL = "critical"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"

ALERT_ESCALATION_RATE = "escalation_rate_high"
ALERT_SLA_BREACH = "sla_breach_detected"
ALERT_P90_LATENCY = "p90_latency_high"
ALERT_SHEETS_SYNC_ERROR = "sheets_sync_error"
ALERT_ERROR_RATE = "error_rate_high"
ALERT_DEAD_LETTERED = "dead_lettered_jobs"

_THRESHOLD_FIELDS = (
    "escalation_rate_pct",
    "sla_breach_count",
    "p90_latency_ms",
    "error_rate_pct",
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _state_key(tenant_id: str) -> str:
    return f"{THRESHOLD_STATE_KEY_PREFIX}:{tenant_id}"


def default_thresholds() -> dict[str, float]:
    settings = get_settings()
    return {
        "escalation_rate_pct": float(settings.alert_escalation_rate_threshold),
        "sla_breach_count": float(settings.alert_sla_breach_count_threshold),
        "p90_latency_ms": float(settings.alert_p90_latency_ms_threshold),
        "error_rate_pct": float(settings.alert_error_rate_threshold),
    }


def get_alert_thresholds(db: Session, tenant_id: str) -> dict[str, float]:
    """Return the tenant's effective thresholds, falling back to platform defaults."""

    thresholds = default_thresholds()
    row = db.get(AgentState, _state_key(tenant_id))
    if row is None:
        return thresholds
    try:
        stored = json.loads(row.value_json or "{}")
    except (TypeError, ValueError):
        return thresholds
    if not isinstance(stored, dict):
        return thresholds
    for field in _THRESHOLD_FIELDS:
        value = stored.get(field)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0:
            thresholds[field] = float(value)
    return thresholds


def set_alert_thresholds(db: Session, tenant_id: str, overrides: dict[str, Any]) -> dict[str, float]:
    """Persist validated threshold overrides for one tenant."""

    cleaned: dict[str, float] = {}
    for field in _THRESHOLD_FIELDS:
        value = overrides.get(field)
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise ValueError(f"invalid threshold: {field}")
        cleaned[field] = float(value)

    key = _state_key(tenant_id)
    row = db.get(AgentState, key)
    payload = json.dumps(cleaned, sort_keys=True, separators=(",", ":"))
    if row is None:
        db.add(AgentState(key=key, tenant_id=tenant_id, value_json=payload))
    else:
        row.tenant_id = tenant_id
        row.value_json = payload
    db.flush()
    return get_alert_thresholds(db, tenant_id)


def _alert(code: str, severity: str, message: str, *, observed: Any, threshold: Any) -> dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "observed": observed,
        "threshold": threshold,
    }


def evaluate_alerts(
    *,
    tenant_id: str,
    kpis: dict[str, Any],
    health: dict[str, Any],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    """Compare aggregates against thresholds and return triggered alerts.

    Pure function: no database, no network, no side effect. The route and the
    dispatcher both call this so the in-app badge and any outbound notification
    always describe the same evaluation.
    """

    alerts: list[dict[str, Any]] = []

    escalation_rate = float(kpis.get("escalation_rate") or 0.0)
    escalation_threshold = thresholds["escalation_rate_pct"]
    # A rate over an empty period is 0%, so this cannot fire on no traffic.
    if kpis.get("total_calls") and escalation_rate > escalation_threshold:
        alerts.append(
            _alert(
                ALERT_ESCALATION_RATE,
                SEVERITY_CRITICAL if escalation_rate >= escalation_threshold * 1.5 else SEVERITY_WARNING,
                f"Escalation rate is {escalation_rate}% against a {escalation_threshold}% threshold.",
                observed=escalation_rate,
                threshold=escalation_threshold,
            )
        )

    breaches = int(kpis.get("sla_breached_count") or 0)
    if breaches > thresholds["sla_breach_count"]:
        alerts.append(
            _alert(
                ALERT_SLA_BREACH,
                SEVERITY_CRITICAL,
                f"{breaches} open escalation(s) are past their SLA deadline.",
                observed=breaches,
                threshold=thresholds["sla_breach_count"],
            )
        )

    p90 = float(kpis.get("p90_turn_latency_ms") or 0.0)
    if p90 > thresholds["p90_latency_ms"]:
        alerts.append(
            _alert(
                ALERT_P90_LATENCY,
                SEVERITY_WARNING,
                f"P90 turn latency is {round(p90)}ms against a {round(thresholds['p90_latency_ms'])}ms threshold.",
                observed=round(p90),
                threshold=round(thresholds["p90_latency_ms"]),
            )
        )

    if health.get("sheets_mirror_status") == "error":
        alerts.append(
            _alert(
                ALERT_SHEETS_SYNC_ERROR,
                SEVERITY_WARNING,
                "The Google Sheets mirror reported an error and is no longer writing call rows.",
                observed="error",
                threshold="connected",
            )
        )

    error_rate = float(health.get("error_rate_24h") or 0.0)
    if error_rate > thresholds["error_rate_pct"]:
        alerts.append(
            _alert(
                ALERT_ERROR_RATE,
                SEVERITY_CRITICAL if error_rate >= thresholds["error_rate_pct"] * 2 else SEVERITY_WARNING,
                f"Call error rate over 24h is {error_rate}% against a {thresholds['error_rate_pct']}% threshold.",
                observed=error_rate,
                threshold=thresholds["error_rate_pct"],
            )
        )

    dead_lettered = int(health.get("dead_lettered_recent_count") or 0)
    if dead_lettered:
        alerts.append(
            _alert(
                ALERT_DEAD_LETTERED,
                SEVERITY_CRITICAL,
                f"{dead_lettered} durable job(s) dead-lettered in the last 24 hours.",
                observed=dead_lettered,
                threshold=0,
            )
        )

    if any(item["severity"] == SEVERITY_CRITICAL for item in alerts):
        state = SEVERITY_CRITICAL
    elif alerts:
        state = SEVERITY_WARNING
    else:
        state = "ok"

    return {
        "tenant_id": tenant_id,
        "evaluated_at": _utcnow().isoformat(),
        "state": state,
        "alert_count": len(alerts),
        "critical_count": sum(1 for item in alerts if item["severity"] == SEVERITY_CRITICAL),
        "alerts": alerts,
        "thresholds": thresholds,
    }


def alert_channels(tenant: Tenant) -> dict[str, Any]:
    """Describe which delivery channels are configured, without exposing them.

    The fallback email and webhook URL are customer contact data; only their
    presence is reported so an operator can confirm routing is wired up.
    """

    return {
        "email": {
            "configured": bool((tenant.fallback_email or "").strip()),
            "transport": "durable_notification_worker",
        },
        "webhook": {
            "configured": bool((tenant.webhook_url or "").strip()),
            "signed": bool((tenant.webhook_secret or "").strip()),
            "transport": "durable_notification_worker",
        },
        "in_app": {"configured": True, "transport": "observability_alert_badge"},
    }


def _dispatch_idempotency_key(tenant_id: str, reason: str, codes: list[str], bucket: str) -> str:
    """One notification per tenant/reason/alert-set per minute bucket.

    A dashboard that polls every 30 seconds must not enqueue a duplicate alert
    on every refresh, and the durable ledger enforces uniqueness on this key.
    """

    material = json.dumps(
        {"bucket": bucket, "codes": sorted(codes), "reason": reason, "tenant_id": tenant_id},
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"alert:{hashlib.sha256(material.encode()).hexdigest()[:48]}"


def dispatch_alert_notification(
    db: Session,
    *,
    tenant_id: str,
    evaluation: dict[str, Any],
    reason: str = "threshold_breach",
) -> dict[str, Any]:
    """Enqueue one durable notification intent for a triggered evaluation.

    Returns a receipt describing what was queued and which channels the worker
    will use. No mail is sent and no webhook is called from this process.
    """

    settings = get_settings()
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError("tenant_not_found")

    channels = alert_channels(tenant)
    codes = [item["code"] for item in evaluation.get("alerts", [])]
    if not settings.alerting_enabled:
        return {
            "queued": False,
            "reason": "alerting_disabled",
            "channels": channels,
            "alert_codes": codes,
        }

    bucket = _utcnow().strftime("%Y%m%d%H%M")
    result = enqueue_side_effect(
        db,
        tenant_id=tenant_id,
        effect_type=NOTIFICATION_DISPATCH,
        aggregate_type="observability_alert",
        aggregate_id=tenant_id,
        idempotency_key=_dispatch_idempotency_key(tenant_id, reason, codes, bucket),
        priority=10 if evaluation.get("state") == SEVERITY_CRITICAL else 0,
        payload={"alert_codes": codes, "state": evaluation.get("state", "ok")},
    )
    return {
        "queued": True,
        "created": result.created,
        "reason": reason,
        "intent_id": result.intent_id,
        "job_id": result.job_id,
        "outbox_id": result.outbox_id,
        "channels": channels,
        "alert_codes": codes,
        "state": evaluation.get("state"),
        "execution": "durable_worker_owned",
        "inline_delivery": False,
    }
