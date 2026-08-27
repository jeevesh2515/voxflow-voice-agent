"""Day 46 exact inbound routing and secure caller-verification tests."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select

from voxflow_api import auth
from voxflow_api.agent.runner import AgentTurnResult
from voxflow_api.agent.tools import check_po_status, create_po, verify_pin
from voxflow_api.auth import AuthUser, normalized_email_hash
from voxflow_api.config import get_settings
from voxflow_api.db import (
    Supplier,
    TenantMember,
    TenantPhoneNumber,
    reset_db,
    session_scope,
)
from voxflow_api.main import create_app
from voxflow_api.routes.connect import _resolve_connect_route
from voxflow_api.routes.ws import get_pipeline
from voxflow_api.seed import seed
from voxflow_api.services.data_ingestion import ingest_csv_data, validate_csv_data
from voxflow_api.services.pin_security import verify_pin_hash
from voxflow_api.voice.pipeline import CallSession


IDENTITIES = {
    "owner-token": AuthUser(user_id="day46-owner", email="owner@day46.test"),
    "operator-token": AuthUser(user_id="day46-operator", email="operator@day46.test"),
    "viewer-token": AuthUser(user_id="day46-viewer", email="viewer@day46.test"),
    "amul-owner-token": AuthUser(user_id="day46-amul-owner", email="amul-owner@day46.test"),
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
        invited_by="day46-test",
        activated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def day46_client(monkeypatch):
    monkeypatch.setenv("TENANT_AUTHORIZATION_ENFORCED", "true")
    get_settings.cache_clear()
    monkeypatch.setattr(auth, "_verify_token", lambda token: IDENTITIES.get(token))
    reset_db()
    seed(reset=True)
    with session_scope() as db:
        db.add_all(
            [
                _membership("tm-day46-owner", "varun", "day46-owner", "owner@day46.test", "owner"),
                _membership("tm-day46-operator", "varun", "day46-operator", "operator@day46.test", "operator"),
                _membership("tm-day46-viewer", "varun", "day46-viewer", "viewer@day46.test", "viewer"),
                _membership("tm-day46-amul", "amul", "day46-amul-owner", "amul-owner@day46.test", "owner"),
            ]
        )
    with TestClient(create_app()) as client:
        yield client
    get_settings.cache_clear()


def test_owner_configures_exact_route_and_cross_tenant_takeover_is_blocked(day46_client):
    created = day46_client.post(
        "/api/tenants/varun/phone-numbers",
        headers=_headers("owner-token"),
        json={
            "phone_number": "+44 (20) 7946-0958",
            "label": "Enhanced Hindi Connect line",
            "provider": "connect",
            "verification_mode": "enhanced",
            "route_language": "hi",
            "active": True,
        },
    )
    assert created.status_code == 200
    created_body = created.json()
    assert created_body == {
        "ok": True,
        "phone_number": "+442079460958",
        "tenant_id": "varun",
        "label": "Enhanced Hindi Connect line",
        "provider": "connect",
        "verification_mode": "enhanced",
        "route_language": "hi",
        "active": True,
        "created_at": created_body["created_at"],
        "updated_at": created_body["updated_at"],
    }
    assert created_body["created_at"]
    assert created_body["updated_at"]

    viewer_list = day46_client.get(
        "/api/tenants/varun/telephony",
        headers=_headers("viewer-token"),
    )
    assert viewer_list.status_code == 200
    viewer_body = viewer_list.json()
    assert viewer_body["routing_mode"] == "exact_did"
    assert any(row["phone_number"] == "+442079460958" for row in viewer_body["phone_numbers"])
    assert "auth_pin" not in viewer_list.text
    assert "pbkdf2" not in viewer_list.text

    cross_tenant_read = day46_client.get(
        "/api/tenants/varun/telephony",
        headers=_headers("amul-owner-token"),
    )
    assert cross_tenant_read.status_code == 403

    operator_write = day46_client.post(
        "/api/tenants/varun/phone-numbers",
        headers=_headers("operator-token"),
        json={"phone_number": "+442079460959", "provider": "connect"},
    )
    assert operator_write.status_code == 403

    takeover = day46_client.post(
        "/api/tenants/amul/phone-numbers",
        headers=_headers("amul-owner-token"),
        json={"phone_number": "+442079460958", "provider": "connect"},
    )
    assert takeover.status_code == 409
    with session_scope() as db:
        row = db.get(TenantPhoneNumber, "+442079460958")
        assert row is not None
        assert row.tenant_id == "varun"

    invalid = day46_client.post(
        "/api/tenants/varun/phone-numbers",
        headers=_headers("owner-token"),
        json={"phone_number": "020 7946 0958", "provider": "connect"},
    )
    assert invalid.status_code == 422

    updated = day46_client.patch(
        "/api/tenants/varun/phone-numbers/%2B442079460958",
        headers=_headers("owner-token"),
        json={"verification_mode": "standard", "route_language": "en"},
    )
    assert updated.status_code == 200
    assert updated.json()["verification_mode"] == "standard"
    assert updated.json()["route_language"] == "en"

    deactivated = day46_client.delete(
        "/api/tenants/varun/phone-numbers/%2B442079460958",
        headers=_headers("owner-token"),
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["active"] is False
    with pytest.raises(HTTPException) as inactive:
        asyncio.run(_resolve_connect_route("+442079460958"))
    assert inactive.value.status_code == 404


def test_connect_resolution_is_provider_exact_and_starts_session_with_route_policy(day46_client, monkeypatch):
    with session_scope() as db:
        db.add(
            TenantPhoneNumber(
                phone_number="+442079460960",
                tenant_id="amul",
                provider="connect",
                verification_mode="enhanced",
                route_language="hi",
                active=1,
                label="Amul Connect",
            )
        )
        db.add(
            TenantPhoneNumber(
                phone_number="+442079460961",
                tenant_id="varun",
                provider="twilio",
                active=1,
                label="Not Connect",
            )
        )

    route = asyncio.run(_resolve_connect_route("+44 20 7946 0960"))
    assert route["tenant_id"] == "amul"
    assert route["provider"] == "connect"
    assert route["verification_mode"] == "enhanced"
    assert route["language"] == "hi"

    with pytest.raises(HTTPException) as unknown:
        asyncio.run(_resolve_connect_route("+442079460999"))
    assert unknown.value.status_code == 404
    with pytest.raises(HTTPException) as wrong_provider:
        asyncio.run(_resolve_connect_route("+442079460961"))
    assert wrong_provider.value.status_code == 404

    async def fake_turn(self, session, user_text):
        return AgentTurnResult(reply="नमस्ते", actions=[], tool_calls=[], finish_reason="stop")

    monkeypatch.setattr("voxflow_api.routes.connect.AgentRunner.handle_turn", fake_turn)
    response = day46_client.post(
        "/api/connect/turn",
        json={
            "contact_id": "day46-connect-session",
            "customer_phone": "+447700900123",
            "system_phone": "+442079460960",
            "user_text": "नमस्ते",
            "language": "en",
        },
    )
    assert response.status_code == 200
    assert response.json()["language"] == "hi"
    session = get_pipeline().get_session("day46-connect-session")
    assert session is not None
    assert session.tenant_id == "amul"
    assert session.inbound_did == "+442079460960"
    assert session.telephony_provider == "connect"
    assert session.verification_mode == "enhanced"
    assert session.route_policy["route_language"] == "hi"


def test_owner_only_pin_set_hashes_and_status_apis_are_redacted(day46_client):
    supplier_id = "sup-varun-001"
    denied = day46_client.put(
        f"/api/admin/tenants/varun/suppliers/{supplier_id}/caller-pin",
        headers=_headers("operator-token"),
        json={"pin": "8642", "confirm_pin": "8642"},
    )
    assert denied.status_code == 403

    operator_import = day46_client.post(
        "/api/data/suppliers/import?tenant_id=varun",
        headers=_headers("operator-token"),
        json={
            "csv_text": (
                "id,name,phone,auth_pin\n"
                "day46-operator-pin,Operator Caller,+447700900778,9753\n"
            )
        },
    )
    assert operator_import.status_code == 403
    assert "9753" not in operator_import.text

    invalid = day46_client.put(
        f"/api/tenants/varun/caller-verification/{supplier_id}/pin",
        headers=_headers("owner-token"),
        json={"pin": "raw-secret-pin", "confirm_pin": "raw-secret-pin"},
    )
    assert invalid.status_code == 422
    assert "raw-secret-pin" not in invalid.text

    mismatch = day46_client.put(
        f"/api/tenants/varun/caller-verification/{supplier_id}/pin",
        headers=_headers("owner-token"),
        json={"pin": "8642", "confirm_pin": "8643"},
    )
    assert mismatch.status_code == 422
    assert mismatch.json()["detail"] == "pin_confirmation_mismatch"

    updated = day46_client.put(
        f"/api/tenants/varun/caller-verification/{supplier_id}/pin",
        headers=_headers("owner-token"),
        json={"pin": "8642", "confirm_pin": "8642"},
    )
    assert updated.status_code == 200
    assert "8642" not in updated.text
    assert "pbkdf2" not in updated.text

    with session_scope() as db:
        supplier = db.execute(
            select(Supplier).where(Supplier.tenant_id == "varun", Supplier.id == supplier_id)
        ).scalars().one()
        assert supplier.auth_pin is None
        assert supplier.auth_pin_hash is not None
        assert supplier.pin_updated_at is not None
        assert "8642" not in supplier.auth_pin_hash
        assert verify_pin_hash("8642", supplier.auth_pin_hash)

    for token in ("owner-token", "operator-token", "viewer-token"):
        status = day46_client.get(
            "/api/admin/tenants/varun/caller-pins",
            headers=_headers(token),
        )
        assert status.status_code == 200
        body = status.text
        assert "8642" not in body
        assert "auth_pin" not in body
        assert "pbkdf2" not in body

    suppliers = day46_client.get("/api/suppliers?tenant_id=varun", headers=_headers("viewer-token"))
    assert suppliers.status_code == 200
    assert "auth_pin" not in suppliers.text
    assert "8642" not in suppliers.text

    session = CallSession(call_id="day46-hashed-pin", tenant_id="varun", supplier_id=supplier_id)
    result = asyncio.run(verify_pin(session, pin="8642"))
    assert result["verified"] is True
    assert session.pin_verified is True


def test_legacy_plaintext_pin_is_verified_then_migrated(day46_client):
    with session_scope() as db:
        db.add(
            Supplier(
                id="day46-legacy-supplier",
                tenant_id="varun",
                name="Legacy Caller",
                phone="+447700988811",
                city="London",
                state="Greater London",
                pincode="EC1A 1BB",
                auth_pin="2468",
                auth_pin_hash=None,
            )
        )

    session = CallSession(
        call_id="day46-legacy-pin",
        tenant_id="varun",
        supplier_id="day46-legacy-supplier",
    )
    result = asyncio.run(verify_pin(session, pin="2468"))
    assert result["verified"] is True
    with session_scope() as db:
        supplier = db.execute(
            select(Supplier).where(
                Supplier.tenant_id == "varun",
                Supplier.id == "day46-legacy-supplier",
            )
        ).scalars().one()
        assert supplier.auth_pin is None
        assert supplier.auth_pin_hash is not None
        assert supplier.pin_updated_at is not None
        assert verify_pin_hash("2468", supplier.auth_pin_hash)


def test_route_verification_policy_enforces_enhanced_reads_and_pin_writes(day46_client):
    """Authorization is bound to the exact supplier that was verified —
    directly toggling `verified`/`pin_verified` alone no longer authorizes
    reads or writes; the session-local binding must also match."""
    from voxflow_api.agent.tools import _KNOWLEDGE_BINDING_KEY, _PIN_BINDING_KEY

    standard = CallSession(
        call_id="day46-standard",
        tenant_id="varun",
        supplier_id="sup-varun-001",
        verified=True,
        verification_mode="standard",
    )
    standard.route_policy[_KNOWLEDGE_BINDING_KEY] = "sup-varun-001"
    standard_read = asyncio.run(check_po_status(standard, order_id="PO-1717000000-001"))
    assert standard_read["ok"] is True

    enhanced = CallSession(
        call_id="day46-enhanced",
        tenant_id="varun",
        supplier_id="sup-varun-001",
        verified=True,
        verification_mode="enhanced",
    )
    enhanced.route_policy[_KNOWLEDGE_BINDING_KEY] = "sup-varun-001"
    enhanced_without_pin = asyncio.run(check_po_status(enhanced, order_id="PO-1717000000-001"))
    assert enhanced_without_pin["error"] == "pin_required"
    enhanced.pin_verified = True
    enhanced.route_policy[_PIN_BINDING_KEY] = "sup-varun-001"
    enhanced_read = asyncio.run(check_po_status(enhanced, order_id="PO-1717000000-001"))
    assert enhanced_read["ok"] is True

    enhanced.verified = False
    enhanced_knowledge_missing = asyncio.run(check_po_status(enhanced, order_id="PO-1717000000-001"))
    assert enhanced_knowledge_missing["error"] == "not_verified"

    standard.pin_verified = False
    write = asyncio.run(create_po(standard, items=[{"sku": "PEP-250ML-12", "quantity": 1}]))
    assert write["error"] == "pin_required"


def test_supplier_ingestion_hashes_pin_and_redacts_validation_preview(day46_client):
    csv_text = (
        "id,name,phone,city,state,pincode,auth_pin,contact_type\n"
        "day46-imported,Imported Caller,+44 (7700) 900777,London,Greater London,EC1A 1BB,1357,customer\n"
    )
    validation = validate_csv_data("suppliers", csv_text, "varun")
    assert validation.is_valid is True
    assert validation.preview[0]["auth_pin"] == "[REDACTED]"

    with session_scope() as db:
        result = ingest_csv_data(db, "suppliers", csv_text, "varun")
        assert result.success is True
    with session_scope() as db:
        supplier = db.execute(
            select(Supplier).where(Supplier.tenant_id == "varun", Supplier.id == "day46-imported")
        ).scalars().one()
        assert supplier.phone == "+447700900777"
        assert supplier.auth_pin is None
        assert supplier.auth_pin_hash is not None
        assert supplier.pin_updated_at is not None
        assert verify_pin_hash("1357", supplier.auth_pin_hash)
