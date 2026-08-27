"""Validation helpers for exact inbound telephone routing."""
from __future__ import annotations

import re


TELEPHONY_PROVIDERS = frozenset({"connect", "twilio", "telnyx"})
VERIFICATION_MODES = frozenset({"standard", "enhanced"})
ROUTE_LANGUAGES = frozenset({"tenant_default", "en", "hi"})
_E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")


def normalize_e164(value: str) -> str:
    """Normalize common display separators while requiring an E.164 country code."""
    raw = (value or "").strip()
    if not raw:
        raise ValueError("phone_number_required")
    if raw.startswith("00"):
        raw = "+" + raw[2:]
    normalized = re.sub(r"[\s().-]", "", raw)
    if not _E164_RE.fullmatch(normalized):
        raise ValueError("invalid_e164_phone_number")
    return normalized


def validate_provider(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized not in TELEPHONY_PROVIDERS:
        raise ValueError("unsupported_telephony_provider")
    return normalized


def validate_verification_mode(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized not in VERIFICATION_MODES:
        raise ValueError("unsupported_verification_mode")
    return normalized


def validate_route_language(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized not in ROUTE_LANGUAGES:
        raise ValueError("unsupported_route_language")
    return normalized
