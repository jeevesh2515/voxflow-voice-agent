"""Smoke tests for the API and agent. Run with `pytest -q`."""

import os
import sys
from pathlib import Path

# Ensure we can import voxflow_api when running `pytest` from apps/api/
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Force a deterministic test config BEFORE importing the app
os.environ.setdefault("LLM_PROVIDER", "ollama")
os.environ.setdefault("DATABASE_URL", "sqlite:///./voxflow_test.db")

import pytest
from fastapi.testclient import TestClient

from voxflow_api.config import get_settings
from voxflow_api.db import init_db, reset_db
from voxflow_api.main import create_app
from voxflow_api.seed import seed
from voxflow_api.llm.base import LLMProvider, ChatTurn, LLMResponse


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


def test_summary(client):
    r = client.get("/api/summary")
    assert r.status_code == 200
    data = r.json()
    assert data["suppliers"] >= 5
    assert data["orders"] >= 3


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
    assert len(r.json()) >= 3


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


def test_lookup_supplier_tool():
    """Tool dispatch without an LLM."""
    from voxflow_api.agent.tools import execute_tool
    from voxflow_api.voice.pipeline import CallSession

    s = CallSession(call_id="test")
    res = execute_tool("lookup_supplier", {"phone": "+919876543210"}, s)
    assert res["found"] is True
    assert res["name"] == "Sharma Beverages Wholesale"
    assert s.supplier_id == "sup-varun-001"


def test_check_stock_tool():
    from voxflow_api.agent.tools import execute_tool
    from voxflow_api.voice.pipeline import CallSession

    s = CallSession(call_id="test")
    res = execute_tool("check_stock", {"sku": "PEP-250ML-12"}, s)
    assert res["available"] is True
    assert res["total"] > 0


def test_shipment_status_tool():
    from voxflow_api.agent.tools import execute_tool
    from voxflow_api.voice.pipeline import CallSession

    s = CallSession(call_id="test")
    res = execute_tool("get_shipment_status", {"order_id": "PO-1717000000-001"}, s)
    assert res["found"] is True
    assert res["status"] == "in_transit"


def test_create_po_tool():
    from voxflow_api.agent.tools import execute_tool
    from voxflow_api.voice.pipeline import CallSession

    s = CallSession(call_id="test")
    s.supplier_id = "sup-varun-001"
    res = execute_tool(
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
