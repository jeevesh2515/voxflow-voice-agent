"""Tests for Telephony provider abstraction and registry."""

from __future__ import annotations

import pytest

from voxflow_api.telephony.base import IncomingCall, MediaStart, TelephonyProvider
from voxflow_api.telephony.registry import get_telephony_provider, register_telephony_provider
from voxflow_api.telephony.telnyx_provider import TelnyxProvider
from voxflow_api.telephony.twilio_provider import TwilioProvider


def test_registry_returns_twilio_by_default():
    provider = get_telephony_provider()
    assert isinstance(provider, TwilioProvider)
    assert provider.name == "twilio"


def test_registry_returns_telnyx():
    provider = get_telephony_provider("telnyx")
    assert isinstance(provider, TelnyxProvider)
    assert provider.name == "telnyx"


def test_registry_unknown_falls_back_to_twilio():
    provider = get_telephony_provider("nonexistent")
    assert isinstance(provider, TwilioProvider)


def test_telnyx_provider_texml_generation():
    provider = get_telephony_provider("telnyx")
    texml = provider.generate_connect_response("example.com", "/telnyx/media")
    assert "<Response>" in texml
    assert "<Stream url=\"wss://example.com/telnyx/media\" />" in texml
    assert provider.content_type() == "application/xml"


def test_telnyx_incoming_call_parsing_texml():
    provider = get_telephony_provider("telnyx")
    form = {
        "CallSid": "call-12345",
        "From": "+14155552671",
        "To": "+14155559999",
    }
    incoming = provider.parse_incoming_call(form)
    assert incoming.call_sid == "call-12345"
    assert incoming.caller_phone == "+14155552671"
    assert incoming.to_number == "+14155559999"
    assert incoming.provider == "telnyx"


def test_telnyx_incoming_call_parsing_v2_json():
    provider = get_telephony_provider("telnyx")
    payload = {
        "data": {
            "event_type": "call.initiated",
            "payload": {
                "call_control_id": "cc-9988",
                "from": "+919876543210",
                "to": "+14155551234",
            },
        }
    }
    incoming = provider.parse_incoming_call(payload)
    assert incoming.call_sid == "cc-9988"
    assert incoming.caller_phone == "+919876543210"
    assert incoming.to_number == "+14155551234"
    assert incoming.provider == "telnyx"
