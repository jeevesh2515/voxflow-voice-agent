"""Provider registry — single lookup point for telephony adapters."""

from __future__ import annotations

from typing import Dict, Type

from .base import TelephonyProvider
from .connect_provider import ConnectProvider
from .telnyx_provider import TelnyxProvider
from .twilio_provider import TwilioProvider

_PROVIDERS: Dict[str, Type[TelephonyProvider]] = {
    "twilio": TwilioProvider,
    "telnyx": TelnyxProvider,
    "connect": ConnectProvider,
}

_INSTANCES: Dict[str, TelephonyProvider] = {}


def get_telephony_provider(name: str = "twilio") -> TelephonyProvider:
    """Return a singleton instance of the requested telephony provider.
    
    Defaults to 'twilio' if name is unrecognized or unspecified.
    """
    key = (name or "twilio").lower().strip()
    if key not in _INSTANCES:
        cls = _PROVIDERS.get(key, TwilioProvider)
        _INSTANCES[key] = cls()
    return _INSTANCES[key]


def register_telephony_provider(name: str, provider_cls: Type[TelephonyProvider]) -> None:
    """Register a custom or dynamic telephony provider class."""
    _PROVIDERS[name.lower().strip()] = provider_cls
    _INSTANCES.pop(name.lower().strip(), None)
