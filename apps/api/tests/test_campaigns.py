"""Unit & integration tests for Day 24 Outbound Campaigns API & Worker."""

import pytest
from fastapi.testclient import TestClient

from voxflow_api.db import reset_db
from voxflow_api.main import create_app
from voxflow_api.seed import seed


@pytest.fixture
def app(monkeypatch):
    reset_db()
    seed(reset=True)

    async def mock_place_call(self, to_number, instruction, voice_gender="female", language=None, max_duration_seconds=None):
        return {"ok": True, "call": {"id": f"call-test-{to_number[-4:]}", "status": "completed"}}

    monkeypatch.setattr("voxflow_api.integrations.dial.DialClient.place_outbound_call", mock_place_call)

    app = create_app()
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def test_create_and_list_campaigns(client):
    # 1. Create a draft campaign
    payload = {
        "name": "North Hub Delayed Dispatches",
        "campaign_type": "delayed_shipment",
        "targets": [
            {
                "phone": "+919876543210",
                "name": "Sharma Logistics",
                "context": {"tracking_no": "BD-8899", "carrier": "BlueDart", "revised_eta": "Tomorrow 10 AM"},
            },
            {
                "phone": "+919876543211",
                "name": "Gupta Distributors",
                "context": {"tracking_no": "DL-1122", "carrier": "Delhivery", "revised_eta": "Tomorrow 2 PM"},
            },
        ],
        "auto_start": False,
    }
    r = client.post("/api/campaigns?tenant_id=varun", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["name"] == "North Hub Delayed Dispatches"
    assert data["total_targets"] == 2
    campaign_id = data["id"]

    # 2. List campaigns
    r_list = client.get("/api/campaigns?tenant_id=varun")
    assert r_list.status_code == 200
    c_list = r_list.json()
    assert len(c_list) >= 1
    assert any(c["id"] == campaign_id for c in c_list)

    # 3. Get campaign detail
    r_detail = client.get(f"/api/campaigns/{campaign_id}")
    assert r_detail.status_code == 200
    detail = r_detail.json()
    assert detail["id"] == campaign_id
    assert detail["queue_stats"]["queued"] == 2
    assert detail["queue_stats"]["completed"] == 0

    # 4. Get campaign queue
    r_queue = client.get(f"/api/campaigns/{campaign_id}/queue")
    assert r_queue.status_code == 200
    queue = r_queue.json()
    assert len(queue) == 2
    assert queue[0]["status"] == "queued"

    # 5. Stage campaign execution; Day 28 intentionally avoids inline provider calls.
    r_run = client.post(f"/api/campaigns/{campaign_id}/run?tenant_id=varun")
    assert r_run.status_code == 200
    run_res = r_run.json()
    assert run_res["ok"] is True
    assert run_res["processed"] == 0
    assert run_res["execution_mode"] == "staged"

    # 6. Verify targets remain durable and queued for controlled worker rollout.
    r_detail_after = client.get(f"/api/campaigns/{campaign_id}")
    assert r_detail_after.status_code == 200
    detail_after = r_detail_after.json()
    assert detail_after["status"] == "active"
    assert detail_after["successful_calls"] == 0
    assert detail_after["queue_stats"]["queued"] == 2


def test_autostart_campaign(client):
    payload = {
        "name": "PO Verification Flash Campaign",
        "campaign_type": "po_confirmation",
        "targets": [
            {
                "phone": "+919811122233",
                "name": "Agro Bottling Co",
                "context": {"po_id": "PO-991", "item_name": "Sugar Syrup 500L", "quantity": 10},
            }
        ],
        "auto_start": True,
    }
    r = client.post("/api/campaigns?tenant_id=varun", json=payload)
    assert r.status_code == 200
    data = r.json()
    campaign_id = data["id"]

    # Auto-start activates durable staging only; no inline provider call is made.
    r_detail = client.get(f"/api/campaigns/{campaign_id}")
    assert r_detail.status_code == 200
    detail = r_detail.json()
    assert detail["status"] == "active"
    assert detail["successful_calls"] == 0
    assert detail["queue_stats"]["queued"] == 1


def test_nonexistent_campaign_returns_404(client):
    r = client.get("/api/campaigns/nonexistent-id")
    assert r.status_code == 404
