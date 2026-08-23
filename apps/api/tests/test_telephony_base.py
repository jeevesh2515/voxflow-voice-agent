"""Tests for Telephony provider abstraction and registry (Amazon Connect)."""

from __future__ import annotations

from voxflow_api.telephony.connect_provider import ConnectProvider
from voxflow_api.telephony.registry import get_telephony_provider


def test_registry_returns_connect_by_default():
    provider = get_telephony_provider()
    assert isinstance(provider, ConnectProvider)
    assert provider.name == "connect"


def test_registry_returns_connect_explicitly():
    provider = get_telephony_provider("connect")
    assert isinstance(provider, ConnectProvider)
    assert provider.name == "connect"


def test_registry_unknown_falls_back_to_connect():
    provider = get_telephony_provider("nonexistent")
    assert isinstance(provider, ConnectProvider)
    assert provider.name == "connect"


def test_connect_provider_properties():
    provider = get_telephony_provider("connect")
    assert provider.content_type() == "application/json"
    resp = provider.generate_connect_response("example.com", "/api/connect/turn")
    assert "ok" in resp and "connect" in resp

