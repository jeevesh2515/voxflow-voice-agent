"""Day 47 per-tenant agent settings and voice persona configuration tests."""
from __future__ import annotations

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from voxflow_api import auth
from voxflow_api.agent.prompts import PERSONA_GUIDELINES, build_system_prompt, build_tenant_prompt
from voxflow_api.agent.runner import AgentRunner
from voxflow_api.auth import AuthUser, normalized_email_hash
from voxflow_api.config import get_settings
from voxflow_api.db import (
    Tenant,
    TenantMember,
    reset_db,
    session_scope,
)
from voxflow_api.main import create_app
from voxflow_api.seed import seed


IDENTITIES = {
    "owner-token": AuthUser(user_id="day47-owner", email="owner@day47.test"),
    "operator-token": AuthUser(user_id="day47-operator", email="operator@day47.test"),
    "viewer-token": AuthUser(user_id="day47-viewer", email="viewer@day47.test"),
    "amul-owner-token": AuthUser(user_id="day47-amul-owner", email="amul-owner@day47.test"),
}


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _membership(member_id: str, tenant_id: str, user_id: str, email: str, role: str) -> TenantMember:
    return TenantMember(
        id=member_id,
        tenant_id=tenant_id,
        user_id=user_id,
        subject_email_hash=normalized_email_hash(email, fallback_subject=user_id),
        role=role,
        status="active",
        invited_by="day47-test",
        activated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def day47_client(monkeypatch):
    monkeypatch.setenv("TENANT_AUTHORIZATION_ENFORCED", "true")
    get_settings.cache_clear()
    monkeypatch.setattr(auth, "_verify_token", lambda token: IDENTITIES.get(token))

    reset_db()
    seed(reset=True)
    with session_scope() as db:
        db.add_all(
            [
                _membership("mem-owner", "varun", "day47-owner", "owner@day47.test", "owner"),
                _membership("mem-op", "varun", "day47-operator", "operator@day47.test", "operator"),
                _membership("mem-view", "varun", "day47-viewer", "viewer@day47.test", "viewer"),
                _membership("mem-amul-owner", "amul", "day47-amul-owner", "amul-owner@day47.test", "owner"),
            ]
        )

    with TestClient(create_app()) as client:
        yield client
    get_settings.cache_clear()


# ---------- 1. Read Agent Settings (GET) ----------


def test_get_agent_settings_owner(day47_client: TestClient):
    res = day47_client.get("/api/tenants/varun/agent-settings", headers=_headers("owner-token"))
    assert res.status_code == 200
    data = res.json()
    assert data["tenant_id"] == "varun"
    assert data["name"] == "Varun Beverages (PepsiCo)"
    assert data["voice_persona"] == "professional"
    assert data["default_language"] in ("en", "hi")
    assert data["business_hours_enabled"] is False
    assert data["business_hours_start"] == "09:00"
    assert data["business_hours_end"] == "18:00"
    assert data["business_hours_timezone"] == "Asia/Kolkata"
    assert data["fallback_escalation_mode"] == "human_callback"
    assert data["max_verification_failures"] == 3


def test_get_agent_settings_operator_and_viewer(day47_client: TestClient):
    for token in ("operator-token", "viewer-token"):
        res = day47_client.get("/api/tenants/varun/agent-settings", headers=_headers(token))
        assert res.status_code == 200
        assert res.json()["tenant_id"] == "varun"


def test_get_agent_settings_cross_tenant_denied(day47_client: TestClient):
    res = day47_client.get("/api/tenants/varun/agent-settings", headers=_headers("amul-owner-token"))
    assert res.status_code == 403


def test_get_agent_settings_unauthenticated(day47_client: TestClient):
    res = day47_client.get("/api/tenants/varun/agent-settings")
    assert res.status_code == 401


# ---------- 2. Update Agent Settings (PATCH) ----------


def test_patch_agent_settings_owner_success(day47_client: TestClient):
    payload = {
        "agent_name": "Anya",
        "voice_persona": "friendly",
        "default_language": "hi",
        "welcome_message": "Welcome to Varun Beverages dispatch!",
        "system_prompt_override": "Always check cold storage capacity first.",
        "business_hours_enabled": True,
        "business_hours_start": "08:30",
        "business_hours_end": "19:30",
        "business_hours_timezone": "Asia/Kolkata",
        "business_days": "mon,tue,wed,thu,fri,sat",
        "out_of_hours_message": "Our warehouse operates 8:30 AM to 7:30 PM. Please leave your PO number.",
        "fallback_escalation_mode": "transfer",
        "fallback_phone": "+919876543210",
        "fallback_email": "ops@varunbev.com",
        "max_verification_failures": 2,
    }
    res = day47_client.patch(
        "/api/tenants/varun/agent-settings",
        json=payload,
        headers=_headers("owner-token"),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["agent_name"] == "Anya"
    assert data["voice_persona"] == "friendly"
    assert data["default_language"] == "hi"
    assert data["welcome_message"] == "Welcome to Varun Beverages dispatch!"
    assert data["system_prompt_override"] == "Always check cold storage capacity first."
    assert data["business_hours_enabled"] is True
    assert data["business_hours_start"] == "08:30"
    assert data["business_hours_end"] == "19:30"
    assert data["business_days"] == "mon,tue,wed,thu,fri,sat"
    assert data["out_of_hours_message"] == "Our warehouse operates 8:30 AM to 7:30 PM. Please leave your PO number."
    assert data["fallback_escalation_mode"] == "transfer"
    assert data["fallback_phone"] == "+919876543210"
    assert data["fallback_email"] == "ops@varunbev.com"
    assert data["max_verification_failures"] == 2

    # Verify persistence via fresh GET
    get_res = day47_client.get("/api/tenants/varun/agent-settings", headers=_headers("owner-token"))
    assert get_res.status_code == 200
    assert get_res.json()["agent_name"] == "Anya"
    assert get_res.json()["voice_persona"] == "friendly"


def test_patch_agent_settings_operator_forbidden(day47_client: TestClient):
    res = day47_client.patch(
        "/api/tenants/varun/agent-settings",
        json={"voice_persona": "concise"},
        headers=_headers("operator-token"),
    )
    assert res.status_code == 403


def test_patch_agent_settings_viewer_forbidden(day47_client: TestClient):
    res = day47_client.patch(
        "/api/tenants/varun/agent-settings",
        json={"voice_persona": "concise"},
        headers=_headers("viewer-token"),
    )
    assert res.status_code == 403


def test_patch_agent_settings_cross_tenant_forbidden(day47_client: TestClient):
    res = day47_client.patch(
        "/api/tenants/varun/agent-settings",
        json={"voice_persona": "concise"},
        headers=_headers("amul-owner-token"),
    )
    assert res.status_code == 403


# ---------- 3. Validation Rules ----------


def test_patch_agent_settings_invalid_persona(day47_client: TestClient):
    res = day47_client.patch(
        "/api/tenants/varun/agent-settings",
        json={"voice_persona": "super_casual"},
        headers=_headers("owner-token"),
    )
    assert res.status_code == 422
    assert "invalid_voice_persona" in res.json()["detail"]


def test_patch_agent_settings_invalid_language(day47_client: TestClient):
    res = day47_client.patch(
        "/api/tenants/varun/agent-settings",
        json={"default_language": "fr"},
        headers=_headers("owner-token"),
    )
    assert res.status_code == 422
    assert "invalid_default_language" in res.json()["detail"]


def test_patch_agent_settings_invalid_time_format(day47_client: TestClient):
    for bad_time in ("25:00", "8:30", "08:65", "morning"):
        res = day47_client.patch(
            "/api/tenants/varun/agent-settings",
            json={"business_hours_start": bad_time},
            headers=_headers("owner-token"),
        )
        assert res.status_code == 422


def test_patch_agent_settings_invalid_escalation_mode(day47_client: TestClient):
    res = day47_client.patch(
        "/api/tenants/varun/agent-settings",
        json={"fallback_escalation_mode": "drop_call"},
        headers=_headers("owner-token"),
    )
    assert res.status_code == 422
    assert "invalid_fallback_escalation_mode" in res.json()["detail"]


def test_patch_agent_settings_invalid_phone(day47_client: TestClient):
    res = day47_client.patch(
        "/api/tenants/varun/agent-settings",
        json={"fallback_phone": "12345"},
        headers=_headers("owner-token"),
    )
    assert res.status_code == 422
    assert "invalid_fallback_phone" in res.json()["detail"]


def test_patch_agent_settings_invalid_email(day47_client: TestClient):
    res = day47_client.patch(
        "/api/tenants/varun/agent-settings",
        json={"fallback_email": "not-an-email"},
        headers=_headers("owner-token"),
    )
    assert res.status_code == 422
    assert "invalid_fallback_email" in res.json()["detail"]


def test_patch_agent_settings_invalid_verification_failures(day47_client: TestClient):
    for bad_limit in (0, 6, -1):
        res = day47_client.patch(
            "/api/tenants/varun/agent-settings",
            json={"max_verification_failures": bad_limit},
            headers=_headers("owner-token"),
        )
        assert res.status_code == 422


# ---------- 4. Prompt Engine Integration ----------


def test_prompt_builder_all_personas():
    for persona in ("professional", "friendly", "concise", "assertive"):
        prompt = build_system_prompt(voice_persona=persona)
        expected_fragment = PERSONA_GUIDELINES[persona][:30]
        assert expected_fragment in prompt


def test_prompt_builder_business_hours_and_escalation():
    prompt = build_system_prompt(
        business_name="Apex Logistics",
        business_hours_enabled=1,
        business_hours_start="07:00",
        business_hours_end="17:00",
        business_hours_timezone="Europe/London",
        business_days="mon,tue,wed,thu,fri",
        out_of_hours_message="Out of hours shipments are managed by overnight desk.",
        fallback_escalation_mode="transfer",
        fallback_phone="+442079460991",
        max_verification_failures=4,
    )
    assert "Operating hours for Apex Logistics: 07:00 to 17:00 (Europe/London)" in prompt
    assert "Out of hours shipments are managed by overnight desk." in prompt
    assert "initiating a live transfer to our operations desk at +442079460991" in prompt
    assert "allows up to 4 attempts" in prompt


def test_build_tenant_prompt_from_orm_object():
    tenant = Tenant(
        id="test-tenant",
        name="Apex Freight Ltd",
        agent_name="Atlas",
        voice_persona="assertive",
        default_language="en",
        business_hours_enabled=1,
        business_hours_start="08:00",
        business_hours_end="16:00",
        business_hours_timezone="America/New_York",
        business_days="mon,tue,wed,thu,fri",
        fallback_escalation_mode="voicemail",
        fallback_email="dispatch@apexfreight.com",
        max_verification_failures=2,
    )
    prompt = build_tenant_prompt(tenant)
    assert "You are Atlas" in prompt
    assert "Apex Freight Ltd" in prompt
    assert PERSONA_GUIDELINES["assertive"][:30] in prompt
    assert "Operating hours for Apex Freight Ltd: 08:00 to 16:00 (America/New_York)" in prompt
    assert "dispatched to the dispatch team at dispatch@apexfreight.com" in prompt


# ---------- 5. Cache Invalidation ----------


def test_cache_invalidation_upon_settings_update(day47_client: TestClient):
    runner = AgentRunner()
    # Populate cache
    p1 = runner._resolve_tenant_prompt("varun", "en")
    assert "professional" in p1.lower() or "polished" in p1.lower()

    # Update settings to assertive
    res = day47_client.patch(
        "/api/tenants/varun/agent-settings",
        json={"voice_persona": "assertive", "agent_name": "Kavya"},
        headers=_headers("owner-token"),
    )
    assert res.status_code == 200

    # Resolve again — cache was invalidated, so new prompt should reflect updated persona & name
    p2 = runner._resolve_tenant_prompt("varun", "en")
    assert "Kavya" in p2
    assert "authoritative" in p2.lower()
