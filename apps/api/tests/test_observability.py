"""Day 51 observability, KPI aggregation, PII scrubbing, and alerting tests.

Covers:
  - KPI arithmetic (resolution rate, escalation rate, latency percentiles, deltas).
  - Subsystem health derivation and overall status rollup.
  - Operational event redaction (no phone, PIN, name, or order JSON leaves).
  - Tenant isolation: a member of tenant B is refused tenant A's observability.
  - RBAC: viewer/operator cannot trigger or configure alerts; owner can.
  - Sentry/PostHog scrubbers on thrown exceptions and event properties.
  - Alert threshold evaluation and durable (never inline) notification dispatch.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import voxflow_api.auth as auth_mod
from voxflow_api.auth import (
    ROLE_OPERATOR,
    ROLE_OWNER,
    ROLE_VIEWER,
    AuthUser,
    normalized_email_hash,
)
from voxflow_api.config import get_settings
from voxflow_api.db import (
    AgentState,
    Call,
    CommunicationLog,
    JobOutbox,
    JobRun,
    SideEffectIntent,
    Tenant,
    TenantMember,
    TenantPhoneNumber,
    WorksheetLog,
    session_scope,
)
from voxflow_api.main import create_app
from voxflow_api.monitoring import (
    capture_event,
    hash_tenant_id,
    scrub_analytics_properties,
    scrub_sentry_event,
    scrub_value,
)
from voxflow_api.services.alerting_service import (
    ALERT_DEAD_LETTERED,
    ALERT_ERROR_RATE,
    ALERT_ESCALATION_RATE,
    ALERT_P90_LATENCY,
    ALERT_SHEETS_SYNC_ERROR,
    ALERT_SLA_BREACH,
    alert_channels,
    default_thresholds,
    dispatch_alert_notification,
    evaluate_alerts,
    get_alert_thresholds,
    set_alert_thresholds,
)
from voxflow_api.services.observability_service import (
    get_call_kpis,
    get_recent_system_events,
    get_system_health_metrics,
)


TENANT_A = "obs-tenant-a"
TENANT_B = "obs-tenant-b"

USER_A_OWNER = "usr-obs-a-owner"
USER_A_OPERATOR = "usr-obs-a-operator"
USER_A_VIEWER = "usr-obs-a-viewer"
USER_B_OWNER = "usr-obs-b-owner"

AUTH_USERS = {
    USER_A_OWNER: AuthUser(user_id=USER_A_OWNER, email="a-owner@obs.test"),
    USER_A_OPERATOR: AuthUser(user_id=USER_A_OPERATOR, email="a-operator@obs.test"),
    USER_A_VIEWER: AuthUser(user_id=USER_A_VIEWER, email="a-viewer@obs.test"),
    USER_B_OWNER: AuthUser(user_id=USER_B_OWNER, email="b-owner@obs.test"),
}

# Deliberately realistic sensitive values so redaction assertions are meaningful.
LEAK_PHONE = "+919876543210"
LEAK_PIN = "4821"
LEAK_NAME = "Ramesh Kumar"
LEAK_ORDER_JSON = '{"order_id":"po-9911","sku":"SKU-42","amount":128000}'


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _purge(db, tenant_id: str) -> None:
    db.query(SideEffectIntent).filter(SideEffectIntent.tenant_id == tenant_id).delete()
    db.query(JobOutbox).filter(JobOutbox.tenant_id == tenant_id).delete()
    db.query(JobRun).filter(JobRun.tenant_id == tenant_id).delete()
    db.query(WorksheetLog).filter(WorksheetLog.tenant_id == tenant_id).delete()
    db.query(CommunicationLog).filter(CommunicationLog.tenant_id == tenant_id).delete()
    db.query(AgentState).filter(AgentState.tenant_id == tenant_id).delete()
    db.query(Call).filter(Call.tenant_id == tenant_id).delete()
    db.query(TenantPhoneNumber).filter(TenantPhoneNumber.tenant_id == tenant_id).delete()
    db.query(TenantMember).filter(TenantMember.tenant_id == tenant_id).delete()
    db.query(Tenant).filter(Tenant.id == tenant_id).delete()


def _member(member_id: str, tenant_id: str, user_id: str, role: str, now: datetime) -> TenantMember:
    return TenantMember(
        id=member_id,
        tenant_id=tenant_id,
        user_id=user_id,
        subject_email_hash=normalized_email_hash(f"{user_id}@obs.test"),
        role=role,
        status="active",
        activated_at=now,
    )


def _call(
    call_id: str,
    tenant_id: str,
    *,
    started_at: datetime,
    duration_sec: int = 60,
    resolution_status: str = "resolved",
    outcome: str = "completed",
    escalated: int = 0,
    avg_turn_latency_ms: int = 500,
    intent: str = "order_status",
    escalation_status: str = "none",
    sla_due_at: datetime | None = None,
    sheet_synced: int = 1,
) -> Call:
    return Call(
        id=call_id,
        tenant_id=tenant_id,
        started_at=started_at,
        ended_at=started_at + timedelta(seconds=duration_sec),
        duration_sec=duration_sec,
        caller_phone=LEAK_PHONE,
        caller_name=LEAK_NAME,
        language="en",
        intent=intent,
        outcome=outcome,
        escalated=escalated,
        transcript_json=f'[{{"role":"caller","text":"my pin is {LEAK_PIN}"}}]',
        actions_json=f"[{LEAK_ORDER_JSON}]",
        reason=f"Order query from {LEAK_NAME} on {LEAK_PHONE}",
        resolution_status=resolution_status,
        escalation_status=escalation_status,
        sla_due_at=sla_due_at,
        avg_turn_latency_ms=avg_turn_latency_ms,
        sheet_synced=sheet_synced,
        verified=1,
    )


@pytest.fixture
def obs_env(monkeypatch):
    """Seed two isolated tenants with distinguishable call histories."""

    settings = get_settings()
    monkeypatch.setattr(settings, "tenant_authorization_enforced", True)
    monkeypatch.setattr(settings, "demo_mode_enabled", False)
    monkeypatch.setattr(auth_mod, "_verify_token", lambda token: AUTH_USERS.get(token))

    now = _utcnow()
    with session_scope() as db:
        _purge(db, TENANT_A)
        _purge(db, TENANT_B)

        db.add(Tenant(id=TENANT_A, name="Observability Depot A", plan="growth", fallback_email="ops@obs.test"))
        db.add(Tenant(id=TENANT_B, name="Observability Depot B", plan="starter"))
        db.flush()

        db.add(_member("tm-obs-a-owner", TENANT_A, USER_A_OWNER, ROLE_OWNER, now))
        db.add(_member("tm-obs-a-operator", TENANT_A, USER_A_OPERATOR, ROLE_OPERATOR, now))
        db.add(_member("tm-obs-a-viewer", TENANT_A, USER_A_VIEWER, ROLE_VIEWER, now))
        db.add(_member("tm-obs-b-owner", TENANT_B, USER_B_OWNER, ROLE_OWNER, now))

        # Tenant A: 10 calls in window — 6 resolved, 2 escalated, 2 unresolved.
        # Seeded inside the last 24h so the 7-day KPI window and the 24h health
        # window both observe the same rows.
        base = now - timedelta(hours=2)
        for index in range(6):
            db.add(_call(f"call-a-res-{index}", TENANT_A, started_at=base, duration_sec=60, avg_turn_latency_ms=400 + index * 10))
        for index in range(2):
            db.add(
                _call(
                    f"call-a-esc-{index}",
                    TENANT_A,
                    started_at=base,
                    duration_sec=120,
                    resolution_status="unresolved",
                    outcome="escalated",
                    escalated=1,
                    avg_turn_latency_ms=3000,
                    escalation_status="pending",
                    sla_due_at=now - timedelta(minutes=30),
                )
            )
        for index in range(2):
            db.add(
                _call(
                    f"call-a-open-{index}",
                    TENANT_A,
                    started_at=base,
                    duration_sec=30,
                    resolution_status="partial",
                    outcome="failed",
                    avg_turn_latency_ms=800,
                )
            )

        # Tenant B: a single resolved call so a leak would be obvious in counts.
        db.add(_call("call-b-only", TENANT_B, started_at=base, duration_sec=45))

        db.add(
            TenantPhoneNumber(
                phone_number="+14155550001",
                tenant_id=TENANT_A,
                label="Primary",
                provider="twilio",
                active=1,
            )
        )
        db.add(
            WorksheetLog(
                tenant_id=TENANT_A,
                worksheet_name="Call Log",
                action_type="append",
                row_data_json=f'{{"caller":"{LEAK_PHONE}","name":"{LEAK_NAME}","order":{LEAK_ORDER_JSON}}}',
                timestamp=now - timedelta(hours=1),
            )
        )
        db.add(
            CommunicationLog(
                id="comm-obs-a",
                tenant_id=TENANT_A,
                channel="email",
                recipient="supplier@obs.test",
                subject=f"Order for {LEAK_NAME}",
                body=f"Confirm {LEAK_ORDER_JSON} and call {LEAK_PHONE}",
                status="sent",
                timestamp=now - timedelta(hours=2),
            )
        )

    yield

    with session_scope() as db:
        _purge(db, TENANT_A)
        _purge(db, TENANT_B)


@pytest.fixture
def client(obs_env):
    return TestClient(create_app())


def _auth(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {user_id}"}


# --------------------------------------------------------------------------- #
# KPI aggregation
# --------------------------------------------------------------------------- #


def test_call_kpis_compute_resolution_escalation_and_latency(obs_env):
    with session_scope() as db:
        kpis = get_call_kpis(db, TENANT_A, time_range_days=7)

    assert kpis["tenant_id"] == TENANT_A
    assert kpis["total_calls"] == 10
    assert kpis["resolved_calls"] == 6
    assert kpis["resolution_rate"] == 60.0
    assert kpis["escalated_calls"] == 2
    assert kpis["escalation_rate"] == 20.0
    # 6*60 + 2*120 + 2*30 = 660s over 10 calls.
    assert kpis["avg_duration_sec"] == 66
    assert kpis["total_duration_sec"] == 660
    # Two escalations are past their SLA deadline.
    assert kpis["sla_breached_count"] == 2
    # The two 3000ms escalations pull P90 above the median.
    assert kpis["p90_turn_latency_ms"] > kpis["median_turn_latency_ms"]
    assert kpis["latency_distribution"]["sample_count"] == 10
    assert len(kpis["calls_over_time"]) == 7
    assert sum(point["calls"] for point in kpis["calls_over_time"]) == 10
    assert kpis["breakdown"]["reasons"]["order_status"] == 10


def test_call_kpis_empty_tenant_never_divides_by_zero(obs_env):
    with session_scope() as db:
        kpis = get_call_kpis(db, TENANT_B, time_range_days=7)
        kpis["calls_over_time"]  # touch while session is open

    assert kpis["total_calls"] == 1
    assert kpis["resolution_rate"] == 100.0
    assert kpis["escalation_rate"] == 0.0
    # No prior-period traffic means no misleading percentage delta.
    assert kpis["deltas"]["total_calls_pct"] is None


def test_call_kpis_range_is_clamped_to_supported_window(obs_env):
    with session_scope() as db:
        assert get_call_kpis(db, TENANT_A, time_range_days=0)["period"]["days"] == 1
        assert get_call_kpis(db, TENANT_A, time_range_days=100_000)["period"]["days"] == 90


def test_call_kpis_unknown_tenant_raises(obs_env):
    with session_scope() as db:
        with pytest.raises(ValueError, match="tenant_not_found"):
            get_call_kpis(db, "obs-tenant-missing", time_range_days=7)


# --------------------------------------------------------------------------- #
# System health
# --------------------------------------------------------------------------- #


def test_system_health_reports_subsystems_and_error_rate(obs_env):
    with session_scope() as db:
        health = get_system_health_metrics(db, TENANT_A)

    assert health["tenant_id"] == TENANT_A
    assert health["db_pool_latency_ms"] is not None and health["db_pool_latency_ms"] >= 0
    keys = {item["key"] for item in health["subsystems"]}
    assert keys == {"database", "llm", "telephony", "sheets_mirror", "durable_jobs"}
    assert health["outbox_pending_count"] == 0
    assert health["dead_lettered_recent_count"] == 0
    # 2 of 10 recent calls have outcome "failed".
    assert health["error_rate_24h"] == 20.0
    assert health["overall_status"] in {"operational", "degraded", "critical"}
    telephony = next(item for item in health["subsystems"] if item["key"] == "telephony")
    assert telephony["status"] == "operational"
    # A DID is a direct identifier and must not appear in a diagnostic payload.
    assert "+14155550001" not in str(health)


def test_system_health_flags_dead_lettered_jobs_as_critical(obs_env):
    now = _utcnow()
    with session_scope() as db:
        db.add(
            JobRun(
                id="job-obs-dead",
                tenant_id=TENANT_A,
                job_type="notification.dispatch",
                status="dead_lettered",
                idempotency_key="obs-dead-1",
                attempt=6,
                created_at=now,
                updated_at=now,
                finished_at=now,
            )
        )
    with session_scope() as db:
        health = get_system_health_metrics(db, TENANT_A)

    assert health["dead_lettered_recent_count"] == 1
    assert health["overall_status"] == "critical"
    queue = next(item for item in health["subsystems"] if item["key"] == "durable_jobs")
    assert queue["status"] == "critical"


def test_system_health_reports_sheets_mirror_error(obs_env):
    with session_scope() as db:
        tenant = db.get(Tenant, TENANT_A)
        tenant.google_sheet_id = "sheet-obs-a"
        tenant.google_sheet_status = "error"
    with session_scope() as db:
        health = get_system_health_metrics(db, TENANT_A)

    assert health["sheets_mirror_status"] == "error"
    mirror = next(item for item in health["subsystems"] if item["key"] == "sheets_mirror")
    assert mirror["status"] == "degraded"


# --------------------------------------------------------------------------- #
# Event stream redaction
# --------------------------------------------------------------------------- #


def test_recent_events_are_redacted_and_tenant_scoped(obs_env):
    with session_scope() as db:
        payload = get_recent_system_events(db, TENANT_A, limit=50)

    events = payload["events"]
    assert events, "expected seeded operational events"
    types = {event["event_type"] for event in events}
    assert {"call_completed", "escalation_created", "sheet_synced", "did_mapped", "communication_logged"} <= types

    serialized = str(payload)
    assert LEAK_PHONE not in serialized
    assert LEAK_NAME not in serialized
    assert LEAK_PIN not in serialized
    assert "po-9911" not in serialized
    assert "supplier@obs.test" not in serialized
    assert "+14155550001" not in serialized
    # Tenant B's only call must never surface here.
    assert "call-b-only" not in serialized


def test_recent_events_limit_is_bounded(obs_env):
    with session_scope() as db:
        assert get_recent_system_events(db, TENANT_A, limit=0)["limit"] == 1
        assert get_recent_system_events(db, TENANT_A, limit=10_000)["limit"] == 100


# --------------------------------------------------------------------------- #
# Route authorization and tenant isolation
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("path", ["kpis", "health", "events", "alerts"])
def test_observability_reads_allow_every_active_member_role(client, path):
    for user in (USER_A_OWNER, USER_A_OPERATOR, USER_A_VIEWER):
        response = client.get(f"/api/tenants/{TENANT_A}/observability/{path}", headers=_auth(user))
        assert response.status_code == 200, response.text
        assert response.json()["tenant_id"] == TENANT_A


@pytest.mark.parametrize("path", ["kpis", "health", "events", "alerts"])
def test_tenant_b_cannot_read_tenant_a_observability(client, path):
    response = client.get(f"/api/tenants/{TENANT_A}/observability/{path}", headers=_auth(USER_B_OWNER))
    assert response.status_code == 403
    assert response.json()["detail"] == "tenant_membership_required"
    assert "Observability Depot A" not in response.text


def test_anonymous_request_is_rejected(client):
    assert client.get(f"/api/tenants/{TENANT_A}/observability/kpis").status_code == 401


def test_kpi_route_reflects_tenant_scoped_counts(client):
    a = client.get(f"/api/tenants/{TENANT_A}/observability/kpis?days=7", headers=_auth(USER_A_VIEWER)).json()
    b = client.get(f"/api/tenants/{TENANT_B}/observability/kpis?days=7", headers=_auth(USER_B_OWNER)).json()
    assert a["total_calls"] == 10
    assert b["total_calls"] == 1


def test_events_route_never_returns_raw_identifiers(client):
    response = client.get(f"/api/tenants/{TENANT_A}/observability/events?limit=50", headers=_auth(USER_A_OPERATOR))
    assert response.status_code == 200
    body = response.text
    assert LEAK_PHONE not in body and LEAK_NAME not in body and LEAK_PIN not in body and "po-9911" not in body


def test_alert_test_requires_owner_role(client):
    for user, expected in ((USER_A_VIEWER, 403), (USER_A_OPERATOR, 403), (USER_A_OWNER, 200)):
        response = client.post(f"/api/tenants/{TENANT_A}/observability/alerts/test", headers=_auth(user))
        assert response.status_code == expected, f"{user} -> {response.text}"


def test_alert_test_is_denied_across_tenants(client):
    response = client.post(f"/api/tenants/{TENANT_A}/observability/alerts/test", headers=_auth(USER_B_OWNER))
    assert response.status_code == 403


def test_alert_thresholds_update_is_owner_only_and_validated(client):
    assert (
        client.put(
            f"/api/tenants/{TENANT_A}/observability/alerts/thresholds",
            json={"escalation_rate_pct": 10},
            headers=_auth(USER_A_OPERATOR),
        ).status_code
        == 403
    )

    ok = client.put(
        f"/api/tenants/{TENANT_A}/observability/alerts/thresholds",
        json={"escalation_rate_pct": 10, "p90_latency_ms": 1200},
        headers=_auth(USER_A_OWNER),
    )
    assert ok.status_code == 200
    assert ok.json()["thresholds"]["escalation_rate_pct"] == 10.0
    assert ok.json()["thresholds"]["p90_latency_ms"] == 1200.0

    bad = client.put(
        f"/api/tenants/{TENANT_A}/observability/alerts/thresholds",
        json={"escalation_rate_pct": -5},
        headers=_auth(USER_A_OWNER),
    )
    assert bad.status_code == 422


def test_alerts_route_fires_on_tightened_threshold(client):
    client.put(
        f"/api/tenants/{TENANT_A}/observability/alerts/thresholds",
        json={"escalation_rate_pct": 5, "p90_latency_ms": 100, "error_rate_pct": 1},
        headers=_auth(USER_A_OWNER),
    )
    body = client.get(f"/api/tenants/{TENANT_A}/observability/alerts", headers=_auth(USER_A_OWNER)).json()
    codes = {alert["code"] for alert in body["alerts"]}
    assert {ALERT_ESCALATION_RATE, ALERT_P90_LATENCY, ALERT_SLA_BREACH, ALERT_ERROR_RATE} <= codes
    assert body["state"] == "critical"
    # Channel wiring is reported as configured/not, never as a raw address.
    assert body["channels"]["email"]["configured"] is True
    assert "ops@obs.test" not in str(body)


# --------------------------------------------------------------------------- #
# Alerting service
# --------------------------------------------------------------------------- #


def test_threshold_overrides_persist_and_fall_back_to_defaults(obs_env):
    with session_scope() as db:
        assert get_alert_thresholds(db, TENANT_A) == default_thresholds()
        set_alert_thresholds(db, TENANT_A, {"escalation_rate_pct": 12.5})
    with session_scope() as db:
        thresholds = get_alert_thresholds(db, TENANT_A)
    assert thresholds["escalation_rate_pct"] == 12.5
    # Unset fields keep the platform default rather than dropping to zero.
    assert thresholds["p90_latency_ms"] == default_thresholds()["p90_latency_ms"]


def test_set_alert_thresholds_rejects_invalid_values(obs_env):
    with session_scope() as db:
        with pytest.raises(ValueError, match="invalid threshold"):
            set_alert_thresholds(db, TENANT_A, {"p90_latency_ms": -1})
        with pytest.raises(ValueError, match="invalid threshold"):
            set_alert_thresholds(db, TENANT_A, {"error_rate_pct": "high"})


def test_evaluate_alerts_is_quiet_when_every_metric_is_healthy():
    evaluation = evaluate_alerts(
        tenant_id=TENANT_A,
        kpis={"total_calls": 50, "escalation_rate": 3.0, "sla_breached_count": 0, "p90_turn_latency_ms": 900},
        health={"error_rate_24h": 0.5, "sheets_mirror_status": "connected", "dead_lettered_recent_count": 0},
        thresholds=default_thresholds(),
    )
    assert evaluation["state"] == "ok"
    assert evaluation["alerts"] == []


def test_evaluate_alerts_triggers_each_configured_threshold():
    evaluation = evaluate_alerts(
        tenant_id=TENANT_A,
        kpis={"total_calls": 40, "escalation_rate": 45.0, "sla_breached_count": 3, "p90_turn_latency_ms": 4200},
        health={"error_rate_24h": 18.0, "sheets_mirror_status": "error", "dead_lettered_recent_count": 2},
        thresholds=default_thresholds(),
    )
    codes = {alert["code"] for alert in evaluation["alerts"]}
    assert codes == {
        ALERT_ESCALATION_RATE,
        ALERT_SLA_BREACH,
        ALERT_P90_LATENCY,
        ALERT_SHEETS_SYNC_ERROR,
        ALERT_ERROR_RATE,
        ALERT_DEAD_LETTERED,
    }
    assert evaluation["state"] == "critical"
    assert evaluation["critical_count"] >= 1


def test_evaluate_alerts_does_not_fire_on_an_empty_period():
    evaluation = evaluate_alerts(
        tenant_id=TENANT_A,
        kpis={"total_calls": 0, "escalation_rate": 0.0, "sla_breached_count": 0, "p90_turn_latency_ms": 0},
        health={"error_rate_24h": 0.0, "sheets_mirror_status": "not_configured", "dead_lettered_recent_count": 0},
        thresholds=default_thresholds(),
    )
    assert evaluation["alerts"] == []


def test_alert_channels_report_configuration_without_exposing_contacts(obs_env):
    with session_scope() as db:
        tenant = db.get(Tenant, TENANT_A)
        tenant.webhook_url = "https://hooks.obs.test/voxflow"
        tenant.webhook_secret = "shhh"
        channels = alert_channels(tenant)

    assert channels["email"]["configured"] is True
    assert channels["webhook"]["configured"] is True and channels["webhook"]["signed"] is True
    assert channels["in_app"]["configured"] is True
    serialized = str(channels)
    assert "ops@obs.test" not in serialized
    assert "hooks.obs.test" not in serialized
    assert "shhh" not in serialized


def test_dispatch_enqueues_durable_intent_and_never_sends_inline(obs_env):
    evaluation = evaluate_alerts(
        tenant_id=TENANT_A,
        kpis={"total_calls": 10, "escalation_rate": 90.0, "sla_breached_count": 1, "p90_turn_latency_ms": 5000},
        health={"error_rate_24h": 30.0, "sheets_mirror_status": "connected", "dead_lettered_recent_count": 0},
        thresholds=default_thresholds(),
    )
    with session_scope() as db:
        receipt = dispatch_alert_notification(db, tenant_id=TENANT_A, evaluation=evaluation)

    assert receipt["queued"] is True
    assert receipt["inline_delivery"] is False
    assert receipt["execution"] == "durable_worker_owned"

    with session_scope() as db:
        intent = db.get(SideEffectIntent, receipt["intent_id"])
        job = db.get(JobRun, receipt["job_id"])
        assert intent is not None and intent.tenant_id == TENANT_A
        assert intent.effect_type == "notification.dispatch"
        assert intent.status == "queued"
        # The worker owns execution; the API only records intent.
        assert job is not None and job.status == "ready"
        # No alert message text or contact address is persisted on the intent.
        assert LEAK_PHONE not in str(intent.payload_hash)


def test_repeated_dispatch_is_idempotent_within_a_minute(obs_env):
    evaluation = evaluate_alerts(
        tenant_id=TENANT_A,
        kpis={"total_calls": 10, "escalation_rate": 90.0, "sla_breached_count": 0, "p90_turn_latency_ms": 100},
        health={"error_rate_24h": 0.0, "sheets_mirror_status": "connected", "dead_lettered_recent_count": 0},
        thresholds=default_thresholds(),
    )
    with session_scope() as db:
        first = dispatch_alert_notification(db, tenant_id=TENANT_A, evaluation=evaluation)
    with session_scope() as db:
        second = dispatch_alert_notification(db, tenant_id=TENANT_A, evaluation=evaluation)

    assert first["created"] is True
    assert second["created"] is False
    assert first["intent_id"] == second["intent_id"]


def test_dispatch_is_inert_when_alerting_is_disabled(obs_env, monkeypatch):
    monkeypatch.setattr(get_settings(), "alerting_enabled", False)
    evaluation = evaluate_alerts(
        tenant_id=TENANT_A,
        kpis={"total_calls": 10, "escalation_rate": 90.0, "sla_breached_count": 0, "p90_turn_latency_ms": 100},
        health={"error_rate_24h": 0.0, "sheets_mirror_status": "connected", "dead_lettered_recent_count": 0},
        thresholds=default_thresholds(),
    )
    with session_scope() as db:
        receipt = dispatch_alert_notification(db, tenant_id=TENANT_A, evaluation=evaluation)
    assert receipt["queued"] is False
    assert receipt["reason"] == "alerting_disabled"


def test_dispatch_rejects_an_unknown_tenant(obs_env):
    with session_scope() as db:
        with pytest.raises(ValueError, match="tenant_not_found"):
            dispatch_alert_notification(
                db,
                tenant_id="obs-tenant-missing",
                evaluation={"alerts": [], "state": "ok"},
            )


# --------------------------------------------------------------------------- #
# PII scrubbers (Sentry + PostHog)
# --------------------------------------------------------------------------- #


def test_sentry_scrubber_removes_caller_pin_name_and_order_payload():
    try:
        raise RuntimeError(
            f"Verification failed for {LEAK_NAME} at {LEAK_PHONE} with PIN {LEAK_PIN}: {LEAK_ORDER_JSON}"
        )
    except RuntimeError as exc:
        event = {
            "message": str(exc),
            "request": {
                "url": f"https://api.voxflow.test/calls?phone={LEAK_PHONE}",
                "headers": {"Authorization": "Bearer secret-token"},
                "data": {"transcript": "raw turn text", "order": LEAK_ORDER_JSON},
                "cookies": {"session": "secret"},
            },
            "user": {"email": "person@obs.test", "ip_address": "203.0.113.5"},
            "extra": {"caller_phone": LEAK_PHONE, "auth_pin": LEAK_PIN},
            "exception": {
                "values": [
                    {
                        "type": "RuntimeError",
                        "value": str(exc),
                        "stacktrace": {"frames": [{"vars": {"caller_name": LEAK_NAME, "pin": LEAK_PIN}}]},
                    }
                ]
            },
        }
        scrubbed = scrub_sentry_event(event)

    serialized = str(scrubbed)
    assert LEAK_PHONE not in serialized
    assert LEAK_NAME not in serialized
    assert LEAK_PIN not in serialized
    assert "po-9911" not in serialized
    assert "secret-token" not in serialized
    assert "person@obs.test" not in serialized
    assert scrubbed["request"]["url"] == "[redacted-url]"
    assert "user" not in scrubbed and "extra" not in scrubbed


def test_scrub_value_redacts_sensitive_keys_and_free_text():
    scrubbed = scrub_value(
        {
            "caller_phone": LEAK_PHONE,
            "customer_name": LEAK_NAME,
            "auth_pin": LEAK_PIN,
            "order_payload": LEAK_ORDER_JSON,
            "latency_ms": 412,
            "free_text": f"call {LEAK_PHONE} and quote pin {LEAK_PIN}",
        }
    )
    assert scrubbed["caller_phone"] == "[redacted]"
    assert scrubbed["customer_name"] == "[redacted]"
    assert scrubbed["auth_pin"] == "[redacted]"
    assert scrubbed["order_payload"] == "[redacted]"
    # Non-identifying numeric telemetry survives intact.
    assert scrubbed["latency_ms"] == 412
    assert LEAK_PHONE not in scrubbed["free_text"] and LEAK_PIN not in scrubbed["free_text"]


def test_analytics_properties_use_an_allow_list():
    safe = scrub_analytics_properties(
        {
            "latency_ms": 320,
            "resolution_rate": 84.5,
            "surface": "observability_dashboard",
            "caller_phone": LEAK_PHONE,
            "customer_name": LEAK_NAME,
            "pin": LEAK_PIN,
            "order": {"order_id": "po-9911"},
            "transcript": ["turn one", "turn two"],
        }
    )
    assert safe == {"latency_ms": 320, "resolution_rate": 84.5, "surface": "observability_dashboard"}
    assert scrub_analytics_properties(None) == {}


def test_analytics_string_properties_are_scrubbed_and_bounded():
    safe = scrub_analytics_properties({"status": f"{LEAK_PHONE} pin {LEAK_PIN} " + "x" * 200})
    assert LEAK_PHONE not in safe["status"]
    assert LEAK_PIN not in safe["status"]
    assert len(safe["status"]) <= 64


def test_tenant_id_is_hashed_before_leaving_the_process(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "observability_hash_tenant_ids", True)
    hashed = hash_tenant_id(TENANT_A)
    assert hashed.startswith("t_")
    assert TENANT_A not in hashed
    # Stable for the same input so funnels still work.
    assert hashed == hash_tenant_id(TENANT_A)
    assert hashed != hash_tenant_id(TENANT_B)
    assert hash_tenant_id("") == ""

    monkeypatch.setattr(settings, "observability_hash_tenant_ids", False)
    assert hash_tenant_id(TENANT_A) == TENANT_A


def test_capture_event_is_inert_without_a_configured_key(monkeypatch):
    monkeypatch.setattr(get_settings(), "posthog_api_key", "")
    import voxflow_api.monitoring as monitoring_mod

    monkeypatch.setattr(monitoring_mod, "_posthog_client", None)
    monkeypatch.setattr(monitoring_mod, "_posthog_initialized", False)
    assert capture_event("observability_viewed", tenant_id=TENANT_A, properties={"latency_ms": 10}) is False


def test_capture_event_sends_only_scrubbed_properties(monkeypatch):
    import voxflow_api.monitoring as monitoring_mod

    sent: list[dict] = []

    class _FakePostHog:
        def capture(self, **kwargs):
            sent.append(kwargs)

    monkeypatch.setattr(monitoring_mod, "_posthog_client", _FakePostHog())
    monkeypatch.setattr(monitoring_mod, "_posthog_initialized", True)

    assert (
        capture_event(
            "observability_viewed",
            tenant_id=TENANT_A,
            properties={"latency_ms": 42, "caller_phone": LEAK_PHONE, "order": LEAK_ORDER_JSON},
        )
        is True
    )
    assert len(sent) == 1
    payload = sent[0]
    assert payload["event"] == "observability_viewed"
    assert TENANT_A not in payload["distinct_id"]
    assert payload["properties"]["latency_ms"] == 42
    assert "caller_phone" not in payload["properties"]
    assert "order" not in payload["properties"]
    assert LEAK_PHONE not in str(payload)
