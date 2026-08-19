"""Unit tests for Dial integration and outbound calling."""

import pytest
from voxflow_api.integrations.dial import DialClient, get_dial_client


def test_dial_client_initialization():
    client = get_dial_client()
    assert isinstance(client, DialClient)


@pytest.mark.asyncio
async def test_dial_unconfigured_fails_gracefully(monkeypatch):
    monkeypatch.setattr(DialClient, "_get_api_key", lambda self: "")
    client = DialClient()
    assert client.is_configured() is False
    res = await client.place_outbound_call(
        to_number="+919999999999",
        instruction="Test outbound call",
    )
    assert res["ok"] is False
    assert res["error"] == "dial_not_configured"
