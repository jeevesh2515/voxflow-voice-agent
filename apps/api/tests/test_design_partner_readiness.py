"""Tests for non-executable design-partner readiness evidence."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from voxflow_api import auth
from voxflow_api.auth import AuthUser, normalized_email_hash
from voxflow_api.config import get_settings
from voxflow_api.db import TenantMember, reset_db, session_scope
from voxflow_api.main import create_app
from voxflow_api.seed import seed


IDENTITIES = {
    "owner-token": AuthUser(user_id="readiness-owner", email="owner@readiness.test"),
    "outsider-token": AuthUser(user_id="readiness-outsider", email="outsider@readiness.test"),
}


@pytest.fixture
def readiness_client(monkeypatch):
    monkeypatch.setenv("TENANT_AUTHORIZATION_ENFORCED", "true")
    monkeypatch.setenv("DURABLE_CAMPAIGN_WORKER_ENABLED", "false")
    monkeypatch.setenv("DURABLE_CAMPAIGN_DRY_RUN", "true")
    monkeypatch.setenv("DURABLE_SIDE_EFFECTS_WORKER_ENABLED", "false")
    monkeypatch.setenv("DURABLE_SIDE_EFFECTS_DRY_RUN", "true")
    get_settings.cache_clear()
    monkeypatch.setattr(auth, "_verify_token", lambda token: IDENTITIES.get(token))
    reset_db()
    seed(reset=True)
    with session_scope() as db:
        db.add(
            TenantMember(
                id="tm-readiness-owner",
                tenant_id="varun",
                user_id="readiness-owner",
                subject_email_hash=normalized_email_hash("owner@readiness.test", fallback_subject="readiness-owner"),
                role="owner",
                status="active",
                invited_by="test",
                activated_at=datetime.now(timezone.utc),
            )
        )
    with TestClient(create_app()) as client:
        yield client
    get_settings.cache_clear()


def test_readiness_scorecard_is_tenant_scoped_and_reports_non_executable_blockers(readiness_client):
    response = readiness_client.get("/api/design-partner/varun/readiness", headers={"Authorization": "Bearer owner-token"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["automatic_activation"] is False
    assert payload["summary"]["provider_activity_enabled"] is False
    assert payload["summary"]["campaign_worker_enabled"] is False
    assert payload["summary"]["side_effect_worker_enabled"] is False
    blocked_codes = {gate["code"] for gate in payload["gates"] if gate["status"] == "blocked"}
    assert {"customer_authority", "recipient_consent_and_cohort", "telecom_provider_registration", "human_escalation_coverage"}.issubset(blocked_codes)
    assert "phone" not in str(payload).lower()


def test_readiness_rejects_outsider_and_allows_only_fixed_demo_read_access(readiness_client):
    outsider = readiness_client.get("/api/design-partner/varun/readiness", headers={"Authorization": "Bearer outsider-token"})
    demo = readiness_client.get(
        "/api/design-partner/varun/readiness",
        headers={"X-VoxFlow-Demo": "enabled", "X-VoxFlow-Demo-Tenant": "varun"},
    )
    cross_tenant_demo = readiness_client.get(
        "/api/design-partner/amul/readiness",
        headers={"X-VoxFlow-Demo": "enabled", "X-VoxFlow-Demo-Tenant": "varun"},
    )
    assert outsider.status_code == 403
    assert demo.status_code == 200
    assert cross_tenant_demo.status_code == 403
