"""Privacy lifecycle controls are database-only and require tenant membership."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256

import pytest
from fastapi.testclient import TestClient

from voxflow_api import auth
from voxflow_api.auth import AuthUser, normalized_email_hash
from voxflow_api.config import get_settings
from voxflow_api.db import Call, PrivacyRequest, TenantMember, reset_db, session_scope
from voxflow_api.main import create_app
from voxflow_api.seed import seed


IDENTITIES = {
    "owner-token": AuthUser(user_id="privacy-owner", email="owner@privacy.test"),
    "operator-token": AuthUser(user_id="privacy-operator", email="operator@privacy.test"),
    "viewer-token": AuthUser(user_id="privacy-viewer", email="viewer@privacy.test"),
    "outsider-token": AuthUser(user_id="privacy-outsider", email="outsider@privacy.test"),
}


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _membership(member_id: str, user_id: str, email: str, role: str) -> TenantMember:
    return TenantMember(
        id=member_id,
        tenant_id="varun",
        user_id=user_id,
        subject_email_hash=normalized_email_hash(email, fallback_subject=user_id),
        role=role,
        status="active",
        invited_by="privacy-test",
        activated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def privacy_client(monkeypatch):
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
        db.add_all(
            [
                _membership("privacy-owner", "privacy-owner", "owner@privacy.test", "owner"),
                _membership("privacy-operator", "privacy-operator", "operator@privacy.test", "operator"),
                _membership("privacy-viewer", "privacy-viewer", "viewer@privacy.test", "viewer"),
            ]
        )
        call = db.query(Call).filter(Call.tenant_id == "varun").first()
        assert call is not None
        call.transcript_json = '[{"role":"caller","text":"private content"}]'
        call.started_at = datetime.now(timezone.utc) - timedelta(days=60)
    with TestClient(create_app()) as client:
        yield client
    get_settings.cache_clear()


def test_retention_preview_is_aggregate_only_and_requires_membership(privacy_client):
    owner = privacy_client.get("/api/privacy/varun/overview", headers=_headers("owner-token"))
    viewer = privacy_client.get("/api/privacy/varun/overview", headers=_headers("viewer-token"))
    outsider = privacy_client.get("/api/privacy/varun/overview", headers=_headers("outsider-token"))
    assert owner.status_code == 200
    assert viewer.status_code == 200
    assert outsider.status_code == 403
    payload = owner.json()
    assert payload["execution"] == {
        "mode": "preview_only",
        "purge_job_enqueued": False,
        "provider_accessed": False,
        "raw_record_exported": False,
    }
    assert payload["preview"]["transcript_records_eligible_for_review"] >= 1
    assert "private content" not in str(payload)
    assert "caller_phone" not in str(payload)


def test_policy_is_owner_controlled_and_never_enqueues_a_purge(privacy_client):
    denied = privacy_client.put(
        "/api/privacy/varun/policy",
        headers=_headers("viewer-token"),
        json={"call_transcript_retention_days": 7, "communication_retention_days": 7, "recording_retention_days": 0},
    )
    updated = privacy_client.put(
        "/api/privacy/varun/policy",
        headers=_headers("owner-token"),
        json={"call_transcript_retention_days": 7, "communication_retention_days": 14, "recording_retention_days": 0},
    )
    assert denied.status_code == 403
    assert updated.status_code == 200
    assert updated.json()["policy"]["call_transcript_retention_days"] == 7
    assert updated.json()["execution"] == "policy_only_no_purge_enqueued"


def test_access_and_deletion_requests_store_only_subject_hash_and_need_manual_review(privacy_client):
    raw_subject = "+919876543210"
    created = privacy_client.post(
        "/api/privacy/varun/requests",
        headers=_headers("owner-token"),
        json={"request_type": "deletion", "subject_reference": raw_subject},
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["request"]["status"] == "pending_human_review"
    assert raw_subject not in str(payload)
    assert payload["execution"] == "request_recorded_no_export_or_deletion_performed"
    request_id = payload["request"]["id"]

    with session_scope() as db:
        row = db.get(PrivacyRequest, request_id)
        assert row is not None
        assert row.subject_hash == sha256(raw_subject.encode()).hexdigest()
        assert raw_subject not in row.__dict__.values()

    reviewed = privacy_client.post(
        f"/api/privacy/varun/requests/{request_id}/review",
        headers=_headers("owner-token"),
        json={"status": "approved_for_manual_export", "review_note": "Identity must be manually verified before any disclosure."},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["request"]["status"] == "approved_for_manual_export"
    assert reviewed.json()["execution"] == "review_recorded_no_export_or_deletion_performed"


def test_request_ledger_is_redacted_and_operator_visible_but_viewer_and_demo_are_denied(privacy_client):
    privacy_client.post(
        "/api/privacy/varun/requests",
        headers=_headers("owner-token"),
        json={"request_type": "access_export", "subject_reference": "person@example.test"},
    )
    operator = privacy_client.get("/api/privacy/varun/requests", headers=_headers("operator-token"))
    viewer = privacy_client.get("/api/privacy/varun/requests", headers=_headers("viewer-token"))
    demo = privacy_client.get(
        "/api/privacy/varun/requests",
        headers={"X-VoxFlow-Demo": "enabled", "X-VoxFlow-Demo-Tenant": "varun"},
    )
    assert operator.status_code == 200
    assert viewer.status_code == 403
    assert demo.status_code == 403
    assert "person@example.test" not in str(operator.json())
    assert "subject_hash" not in str(operator.json())


def test_demo_reset_is_a_blocked_preview_and_owner_request_only(privacy_client):
    demo_preview = privacy_client.get(
        "/api/privacy/varun/demo-reset-preview",
        headers={"X-VoxFlow-Demo": "enabled", "X-VoxFlow-Demo-Tenant": "varun"},
    )
    demo_request = privacy_client.post(
        "/api/privacy/varun/demo-reset-requests",
        headers={"X-VoxFlow-Demo": "enabled", "X-VoxFlow-Demo-Tenant": "varun"},
    )
    owner_request = privacy_client.post("/api/privacy/varun/demo-reset-requests", headers=_headers("owner-token"))
    assert demo_preview.status_code == 200
    assert demo_preview.json()["execution"] == "blocked_preview_only"
    assert demo_preview.json()["data_deleted"] is False
    assert demo_request.status_code == 403
    assert owner_request.status_code == 200
    assert owner_request.json()["execution"] == "blocked_request_only_no_reset_performed"
