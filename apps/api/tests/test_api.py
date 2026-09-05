"""Smoke tests for the API and agent. Run with `pytest -q`."""

# sys.path and the deterministic test environment are configured in
# conftest.py, which pytest imports before this module — so these imports can
# sit at the top of the file where they belong.
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from voxflow_api.db import close_db_engines, reset_db
from voxflow_api.llm.base import LLMProvider, LLMResponse
from voxflow_api.main import create_app
from voxflow_api.seed import seed


@pytest_asyncio.fixture(scope="module", loop_scope="module", autouse=True)
async def close_async_db_after_module():
    yield
    await close_db_engines()


class FakeLLM(LLMProvider):
    name = "fake"
    model = "fake-1"

    def __init__(self, replies):
        self._replies = list(replies)

    async def chat(self, messages, *, tools=None, temperature=None, max_tokens=None):
        if self._replies:
            r = self._replies.pop(0)
            if isinstance(r, str):
                return LLMResponse(content=r, provider=self.name, model=self.model)
            return LLMResponse(**{**r, "provider": self.name, "model": self.model})
        return LLMResponse(content="...", provider=self.name, model=self.model)

    async def health(self) -> bool:
        return True


@pytest.fixture
def app(monkeypatch):
    reset_db()
    seed(reset=True)
    app = create_app()
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["db_schema_bootstrap_mode"] == "auto"


def test_health_db_touches_the_database(client):
    """The keep-alive route must prove real database traffic, not just liveness.

    ``/api/health`` reads settings only, so it cannot hold a Supabase free-tier
    project open. This asserts ``/api/health/db`` actually reads the schema —
    a non-negative tenant count is only obtainable by querying ``tenants`` —
    so the keep-alive schedule pinging it generates genuine activity.
    """

    r = client.get("/api/health/db")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["dialect"] in {"sqlite", "postgres"}
    assert isinstance(body["tenant_count"], int) and body["tenant_count"] >= 0
    assert body["latency_ms"] >= 0
    assert body["checked_at"]
    assert client.head("/api/health/db").status_code == 200


def test_summary(client):
    r = client.get("/api/summary")
    assert r.status_code == 200
    data = r.json()
    assert data["suppliers"] >= 3
    assert data["orders"] >= 2


def test_suppliers_list(client):
    r = client.get("/api/suppliers")
    assert r.status_code == 200
    suppliers = r.json()
    assert any(s["name"] == "Sharma Beverages Wholesale" for s in suppliers)


def test_supplier_search(client):
    r = client.get("/api/suppliers?q=sharma")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    assert "sharma" in data[0]["name"].lower()


def test_stock(client):
    r = client.get("/api/stock")
    assert r.status_code == 200
    items = r.json()
    assert any(it["sku"] == "PEP-250ML-12" for it in items)


def test_stock_by_warehouse(client):
    r = client.get("/api/stock?warehouse=Gurgaon-WH1")
    assert r.status_code == 200
    items = r.json()
    assert all(it["warehouse"] == "Gurgaon-WH1" for it in items)


def test_orders_list(client):
    r = client.get("/api/orders")
    assert r.status_code == 200
    assert len(r.json()) >= 2


def test_shipments(client):
    r = client.get("/api/shipments")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_calls(client):
    r = client.get("/api/calls")
    assert r.status_code == 200
    calls = r.json()
    assert len(calls) >= 1
    assert calls[0]["transcript"]


def test_create_order(client):
    payload = {
        "supplier_id": "sup-varun-001",
        "items": [{"sku": "PEP-250ML-12", "quantity": 10}],
        "notes": "test order",
    }
    r = client.post("/api/orders", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["total_qty"] == 10
    assert data["status"] == "pending"


@pytest.mark.asyncio(loop_scope="module")
async def test_lookup_supplier_tool():
    """Tool dispatch without an LLM."""
    from voxflow_api.agent.tools import execute_tool
    from voxflow_api.voice.pipeline import CallSession

    s = CallSession(call_id="test")
    res = await execute_tool("lookup_supplier", {"phone": "+919876543210"}, s)
    assert res["found"] is True
    assert res["name"] == "Sharma Beverages Wholesale"
    assert s.supplier_id == "sup-varun-001"


@pytest.mark.asyncio(loop_scope="module")
async def test_check_stock_tool():
    from voxflow_api.agent.tools import execute_tool
    from voxflow_api.voice.pipeline import CallSession

    s = CallSession(call_id="test")
    res = await execute_tool("check_stock", {"sku": "PEP-250ML-12"}, s)
    assert res["available"] is True
    assert res["total"] > 0


@pytest.mark.asyncio(loop_scope="module")
async def test_shipment_status_tool():
    """Shipment reads are a protected lookup and now require the same
    knowledge-verification binding as any other protected read — an
    unverified session must not be able to fetch it."""
    from voxflow_api.agent.tools import execute_tool, lookup_supplier, verify_caller
    from voxflow_api.cache import supplier_cache
    from voxflow_api.voice.pipeline import CallSession

    supplier_cache.clear()
    s = CallSession(call_id="test-shipment-status")
    found = await lookup_supplier(s, phone="+919876543210")
    assert found["found"] is True
    verified = await verify_caller(s, company="Sharma Beverages Wholesale", city_or_gstin="Gurgaon")
    assert verified["verified"] is True

    res = await execute_tool("get_shipment_status", {"order_id": "PO-1717000000-001"}, s)
    assert res["found"] is True
    assert res["status"] == "in_transit"


@pytest.mark.asyncio(loop_scope="module")
async def test_create_po_tool():
    """Tier-2 writes require a PIN bound to the exact verified supplier —
    directly toggling `pin_verified` no longer authorizes the write."""
    from voxflow_api.agent.tools import execute_tool, lookup_supplier, verify_caller, verify_pin
    from voxflow_api.cache import supplier_cache
    from voxflow_api.db import Supplier, session_scope
    from voxflow_api.services.pin_security import hash_pin
    from voxflow_api.voice.pipeline import CallSession

    with session_scope() as db:
        supplier = db.get(Supplier, "sup-varun-001")
        supplier.auth_pin_hash = hash_pin("4321")
        supplier.auth_pin = None

    supplier_cache.clear()
    s = CallSession(call_id="test-create-po")
    found = await lookup_supplier(s, phone="+919876543210")
    assert found["found"] is True
    verified = await verify_caller(s, company="Sharma Beverages Wholesale", city_or_gstin="Gurgaon")
    assert verified["verified"] is True
    pin_result = await verify_pin(s, pin="4321")
    assert pin_result["verified"] is True

    res = await execute_tool(
        "create_po",
        {"items": [{"sku": "PEP-250ML-12", "quantity": 25}, {"sku": "7UP-500ML-24", "quantity": 10}]},
        s,
    )
    assert res["ok"] is True
    assert res["total_qty"] == 35
    assert res["supplier_name"] == "Sharma Beverages Wholesale"


def test_agent_runner_uses_fake_llm(monkeypatch):
    """End-to-end: agent receives a fake tool call from the LLM, executes the tool, replies."""
    import asyncio
    from voxflow_api.voice.pipeline import CallSession
    from voxflow_api.agent.runner import AgentRunner

    fake = FakeLLM([
        # First turn: tool call to look up supplier
        {
            "content": "",
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "lookup_supplier",
                        "arguments": '{"phone": "+919876543210"}',
                    },
                }
            ],
        },
        # Second turn: final text reply
        "हाँ राजेश जी, आपकी मदद के लिए तैयार हूँ।",
    ])

    async def run():
        s = CallSession(call_id="test_agent")
        runner = AgentRunner(llm=fake)
        result = await runner.handle_turn(session=s, user_text="हाँ, मैं राजेश बोल रहा हूँ, Sharma Beverages से")
        return s, result

    s, result = asyncio.run(run())
    assert "राजेश" in result.reply or "मदद" in result.reply
    assert any(a["name"] == "lookup_supplier" for a in result.actions)
    assert s.supplier_id == "sup-varun-001"


def test_active_calls_endpoint(client):
    from voxflow_api.routes.ws import get_pipeline

    pipeline = get_pipeline()
    pipeline._sessions.clear()

    # When no calls are active
    r = client.get("/api/active-calls?tenant_id=varun")
    assert r.status_code == 200
    assert r.json() == []

    # When a session is in-flight
    s = pipeline.start_session(
        caller_phone="+919876543210",
        caller_name="Rajesh Sharma",
        language="hi",
        tenant_id="varun",
        call_id="call_test_active_123",
    )
    s.company_name = "Sharma Beverages Wholesale"
    s.intent = "Order Status"
    s.verified = True

    try:
        r = client.get("/api/active-calls?tenant_id=varun")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["call_id"] == "call_test_active_123"
        assert data[0]["caller_name"] == "Rajesh Sharma"
        assert data[0]["company_name"] == "Sharma Beverages Wholesale"
        assert data[0]["verified"] is True
        assert data[0]["intent"] == "Order Status"

        # Tenant isolation check: query for another tenant should be empty
        r_other = client.get("/api/active-calls?tenant_id=amul")
        assert r_other.status_code == 200
        assert r_other.json() == []
    finally:
        pipeline._sessions.clear()


def test_patch_call_resolution(client):
    # Fetch a seeded call ID
    r = client.get("/api/calls?tenant_id=varun")
    assert r.status_code == 200
    calls = r.json()
    assert len(calls) > 0
    call_id = calls[0]["id"]

    # Patch staff resolution
    patch_payload = {"staff_resolution": "Followed up with distributor. Replacement dispatched."}
    r_patch = client.patch(f"/api/calls/{call_id}/resolution?tenant_id=varun", json=patch_payload)
    assert r_patch.status_code == 200
    data = r_patch.json()
    assert data["staff_resolution"] == "Followed up with distributor. Replacement dispatched."
    assert data["staff_resolved_at"] is not None


def test_workspace_provisioning(client):
    payload = {
        "tenant_id": "acme-logistics",
        "name": "Acme Logistics Global",
        "plan": "scale",
        "admin_name": "Sarah Chen",
        "admin_email": "sarah@acmelogistics.com",
        "phone_number": "+14155550199",
        "seed_starter_data": True,
    }
    r = client.post("/api/workspaces/provision", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["tenant_id"] == "acme-logistics"
    assert data["name"] == "Acme Logistics Global"
    assert data["plan"] == "scale"
    assert data["stats"]["products"] > 0
    assert data["stats"]["suppliers"] > 0
    assert data["stats"]["stock_units"] > 0
    assert data["stats"]["orders"] == 1

    # Verify provisioned tenant is in tenant list
    r_tenants = client.get("/api/tenants")
    assert r_tenants.status_code == 200
    tenants = r_tenants.json()
    assert any(t["id"] == "acme-logistics" for t in tenants)

    # Verify suppliers list for the new tenant
    r_sups = client.get("/api/suppliers?tenant_id=acme-logistics")
    assert r_sups.status_code == 200
    sups = r_sups.json()
    assert len(sups) == 3
    assert any(s["name"] == "Apex Supply & Freight Corp" for s in sups)

    # Verify stock items for the new tenant
    r_stock = client.get("/api/stock?tenant_id=acme-logistics")
    assert r_stock.status_code == 200
    stock = r_stock.json()
    assert len(stock) >= 4

    # Verify orders for the new tenant
    r_orders = client.get("/api/orders?tenant_id=acme-logistics")
    assert r_orders.status_code == 200
    orders = r_orders.json()
    assert len(orders) == 1
    assert orders[0]["status"] == "confirmed"

    # Verify summary for the new tenant
    r_summary = client.get("/api/summary?tenant_id=acme-logistics")
    assert r_summary.status_code == 200
    summ = r_summary.json()
    assert summ["suppliers"] == 3
    assert summ["orders"] == 1
    assert summ["pending_orders"] == 1


def test_workspace_provisioning_idempotency(client):
    payload = {
        "tenant_id": "acme-logistics",
        "name": "Acme Logistics Global v2",
        "plan": "enterprise",
        "seed_starter_data": True,
    }
    r = client.post("/api/workspaces/provision", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["plan"] == "enterprise"

