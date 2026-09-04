from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from voxflow_api.db import SessionLocal, Tenant, TenantMember
from voxflow_api.integrations.gsheets import GoogleSheetsClient
from voxflow_api.main import app
from voxflow_api.routes.integrations import extract_spreadsheet_id


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def test_tenants(monkeypatch) -> tuple[str, str]:
    """Create isolated test tenants with owner, operator, and viewer."""
    from voxflow_api.auth import AuthUser
    import voxflow_api.auth as auth_mod
    from voxflow_api.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "tenant_authorization_enforced", True)
    monkeypatch.setattr(settings, "demo_mode_enabled", False)

    users_map = {
        "owner_u1": AuthUser(user_id="owner_u1", email="owner@varun.com"),
        "operator_u2": AuthUser(user_id="operator_u2", email="operator@varun.com"),
        "viewer_u3": AuthUser(user_id="viewer_u3", email="viewer@varun.com"),
    }
    monkeypatch.setattr(auth_mod, "_verify_token", lambda token: users_map.get(token))

    db = SessionLocal()
    tenant_id = "test_varun_sheets"
    t = db.get(Tenant, tenant_id)
    if not t:
        t = Tenant(
            id=tenant_id,
            name="Varun Beverages Test",
            plan="enterprise",
            google_sheet_id=None,
            google_sheet_status="disconnected",
        )
        db.add(t)

    # Seed members
    members = [
        ("tm_owner_1", "owner_u1", "owner@varun.com", "owner"),
        ("tm_operator_2", "operator_u2", "operator@varun.com", "operator"),
        ("tm_viewer_3", "viewer_u3", "viewer@varun.com", "viewer"),
    ]
    from voxflow_api.auth import normalized_email_hash
    for mid, uid, email, role in members:
        m = (
            db.query(TenantMember)
            .filter(TenantMember.tenant_id == tenant_id, TenantMember.user_id == uid)
            .first()
        )
        if not m:
            m = TenantMember(
                id=mid,
                tenant_id=tenant_id,
                user_id=uid,
                subject_email_hash=normalized_email_hash(email),
                role=role,
                status="active",
            )
            db.add(m)
        else:
            m.role = role
            m.status = "active"

    db.commit()
    db.close()
    return tenant_id, "owner_u1"


def test_extract_spreadsheet_id_url_formats():
    """Test URL parser extracts ID from different Google Sheets URL structures."""
    sample_id = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"

    # Full edit URL
    url1 = f"https://docs.google.com/spreadsheets/d/{sample_id}/edit#gid=0"
    assert extract_spreadsheet_id(url1) == sample_id

    # Sharing URL with query parameters
    url2 = f"https://docs.google.com/spreadsheets/d/{sample_id}/edit?usp=sharing"
    assert extract_spreadsheet_id(url2) == sample_id

    # View URL
    url3 = f"https://docs.google.com/spreadsheets/d/{sample_id}/view"
    assert extract_spreadsheet_id(url3) == sample_id

    # Raw sheet ID with spaces
    assert extract_spreadsheet_id(f"  {sample_id}  ") == sample_id


def test_tenant_google_sheets_config_endpoint(client: TestClient, test_tenants: tuple[str, str]):
    tenant_id, _ = test_tenants
    resp = client.get(
        f"/api/tenants/{tenant_id}/integrations/google-sheets",
        headers={"Authorization": "Bearer viewer_u3"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["tenant_id"] == tenant_id
    assert "service_account_email" in data
    assert data["google_sheet_tab"] == "Call Log"


def test_connect_sheet_rbac_enforcement(client: TestClient, test_tenants: tuple[str, str], monkeypatch):
    tenant_id, _ = test_tenants
    sheet_id = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"

    # Mock Sheets verification
    async def mock_verify(*args, **kwargs):
        return {"ok": True, "title": "Varun Live Calls", "tabs": ["Call Log", "Email Log"]}

    monkeypatch.setattr(GoogleSheetsClient.instance(), "verify_and_bootstrap_spreadsheet", mock_verify)

    # 1. Viewer attempt -> 403 Forbidden
    resp = client.post(
        f"/api/tenants/{tenant_id}/integrations/google-sheets/connect",
        json={"sheet_url_or_id": sheet_id},
        headers={"Authorization": "Bearer viewer_u3"},
    )
    assert resp.status_code == 403

    # 2. Operator attempt -> 403 Forbidden
    resp = client.post(
        f"/api/tenants/{tenant_id}/integrations/google-sheets/connect",
        json={"sheet_url_or_id": sheet_id},
        headers={"Authorization": "Bearer operator_u2"},
    )
    assert resp.status_code == 403

    # 3. Owner attempt -> 200 OK
    resp = client.post(
        f"/api/tenants/{tenant_id}/integrations/google-sheets/connect",
        json={
            "sheet_url_or_id": f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit",
            "sheet_name": "Varun Production Live Mirror",
            "call_tab": "Live Calls",
            "email_tab": "Email Log",
        },
        headers={"Authorization": "Bearer owner_u1"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["google_sheet_id"] == sheet_id
    assert data["google_sheet_name"] == "Varun Production Live Mirror"
    assert data["google_sheet_tab"] == "Live Calls"
    assert data["google_sheet_status"] == "connected"


def test_test_connection_and_disconnect(client: TestClient, test_tenants: tuple[str, str], monkeypatch):
    tenant_id, _ = test_tenants

    async def mock_meta(*args, **kwargs):
        return {"ok": True, "title": "Varun Production Live Mirror", "tabs": ["Live Calls", "Email Log"]}

    monkeypatch.setattr(GoogleSheetsClient.instance(), "get_spreadsheet_metadata", mock_meta)

    # Test connection endpoint
    resp = client.post(
        f"/api/tenants/{tenant_id}/integrations/google-sheets/test",
        headers={"Authorization": "Bearer operator_u2"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["title"] == "Varun Production Live Mirror"

    # Disconnect by viewer -> 403
    resp = client.delete(
        f"/api/tenants/{tenant_id}/integrations/google-sheets",
        headers={"Authorization": "Bearer viewer_u3"},
    )
    assert resp.status_code == 403

    # Disconnect by owner -> 200
    resp = client.delete(
        f"/api/tenants/{tenant_id}/integrations/google-sheets",
        headers={"Authorization": "Bearer owner_u1"},
    )
    assert resp.status_code == 200
    assert resp.json()["google_sheet_status"] == "disconnected"


@pytest.mark.asyncio
async def test_append_call_outcome_per_tenant_resolution(monkeypatch):
    """Verify append_call_outcome dynamically routes to tenant's configured spreadsheet ID."""
    db = SessionLocal()
    tenant_id = "test_custom_sheet_tenant"
    t = db.get(Tenant, tenant_id)
    custom_sheet_id = "1CustomVarunSheetId999999999999999999999"
    if not t:
        t = Tenant(
            id=tenant_id,
            name="Custom Sheet Tenant",
            plan="growth",
            google_sheet_id=custom_sheet_id,
            google_sheet_tab="Custom Calls",
            google_sheet_status="connected",
        )
        db.add(t)
    else:
        t.google_sheet_id = custom_sheet_id
        t.google_sheet_tab = "Custom Calls"
        t.google_sheet_status = "connected"
    db.commit()
    db.close()

    recorded_calls = []

    async def mock_append_row(values, tab=None, headers=None, target_sheet_id=None):
        recorded_calls.append({
            "values": values,
            "tab": tab,
            "target_sheet_id": target_sheet_id,
        })
        return {"ok": True, "tab": tab, "updated_range": f"{tab}!A1:Z1"}

    gsheets = GoogleSheetsClient.instance()
    monkeypatch.setattr(gsheets, "append_row", mock_append_row)

    sample_call_row = {
        "call_id": "call_test_12345",
        "caller_phone": "+919876543210",
        "caller_name": "Rajesh Kumar",
        "company": "Varun Beverages",
        "verified": True,
        "language": "hi",
        "reason": "PO status inquiry",
        "solution": "Order confirmed",
        "resolution_status": "resolved",
        "satisfaction": "satisfied",
        "duration_sec": 45,
        "tenant_id": tenant_id,
    }

    res = await gsheets.append_call_outcome(sample_call_row, tenant_id=tenant_id)
    assert res["ok"] is True
    assert len(recorded_calls) == 1
    assert recorded_calls[0]["target_sheet_id"] == custom_sheet_id
    assert recorded_calls[0]["tab"] == "Custom Calls"


@pytest.mark.asyncio
async def test_edit_sheet_row_tool_execution(monkeypatch):
    """Test voice agent edit_sheet_row tool execution updates tenant connected sheet."""
    from voxflow_api.agent.tools import edit_sheet_row
    from voxflow_api.voice.pipeline import CallSession

    tenant_id = "test_custom_sheet_tenant"
    session = CallSession(
        call_id="call-sheet-edit-1",
        tenant_id=tenant_id,
        caller_phone="+919876543210",
        caller_name="Varun Rep",
    )

    recorded_updates = []

    async def mock_update_row_by_key(match_column, match_value, update_values, tab=None, target_sheet_id=None):
        recorded_updates.append({
            "match_column": match_column,
            "match_value": match_value,
            "update_values": update_values,
            "tab": tab,
            "target_sheet_id": target_sheet_id,
        })
        return {
            "ok": True,
            "action": "updated",
            "tab": tab,
            "row_number": 4,
            "updates": ["Status='Delivered'", "Confirmed ETA='Today 4 PM'"],
        }

    gsheets = GoogleSheetsClient.instance()
    monkeypatch.setattr(gsheets, "update_row_by_key", mock_update_row_by_key)

    res = await edit_sheet_row(
        session=session,
        worksheet_name="Orders",
        search_column="PO Number",
        search_value="PO-1002",
        updates={"Status": "Delivered", "Confirmed ETA": "Today 4 PM"},
    )

    assert res["ok"] is True
    assert res["action"] == "updated"
    assert res["row_number"] == 4
    assert len(recorded_updates) == 1
    assert recorded_updates[0]["match_column"] == "PO Number"
    assert recorded_updates[0]["match_value"] == "PO-1002"
    assert recorded_updates[0]["update_values"]["Status"] == "Delivered"
    assert recorded_updates[0]["target_sheet_id"] == "1CustomVarunSheetId999999999999999999999"


def test_build_tenant_prompt_with_connected_sheet():
    """Verify prompt builder injects connected Google Spreadsheet instructions."""
    from voxflow_api.agent.prompts import build_tenant_prompt

    class MockTenant:
        id = "varun"
        name = "Varun Beverages"
        agent_name = "Vaani"
        default_language = "en"
        system_prompt_override = "Be helpful."
        voice_persona = "professional"
        business_hours_enabled = 0
        business_hours_start = "09:00"
        business_hours_end = "18:00"
        business_hours_timezone = "Asia/Kolkata"
        business_days = "mon,tue,wed,thu,fri"
        out_of_hours_message = None
        fallback_escalation_mode = "human_callback"
        fallback_phone = None
        fallback_email = None
        max_verification_failures = 3
        google_sheet_id = "1VarunSheetTestId"
        google_sheet_name = "Varun Beverages Live Ops Mirror"

    prompt = build_tenant_prompt(MockTenant())
    assert "Connected Google Spreadsheet: 'Varun Beverages Live Ops Mirror'" in prompt
    assert "update_worksheet" in prompt
    assert "edit_sheet_row" in prompt


def test_col_to_letter_helper():
    """Verify 0-indexed column integer maps to spreadsheet column names."""
    gsheets = GoogleSheetsClient.instance()
    assert gsheets._col_to_letter(0) == "A"
    assert gsheets._col_to_letter(25) == "Z"
    assert gsheets._col_to_letter(26) == "AA"
    assert gsheets._col_to_letter(27) == "AB"



