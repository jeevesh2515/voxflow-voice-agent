"""Secure caller-PIN storage and backward-compatible verification."""
from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from dataclasses import asdict, is_dataclass
from typing import Any


PIN_SCHEME = "pbkdf2_sha256"
PIN_ITERATIONS = 310_000
PIN_SALT_BYTES = 16
PIN_DIGEST_BYTES = 32
_SPOKEN_PIN_RE = re.compile(r"(?<!\d)\d{4,8}(?!\d)")


def validate_pin(pin: str) -> str:
    """Return a normalized PIN or reject values unsafe for voice verification."""
    normalized = (pin or "").strip()
    if not normalized.isascii() or not normalized.isdigit() or not 4 <= len(normalized) <= 8:
        raise ValueError("pin_must_be_4_to_8_digits")
    return normalized


def hash_pin(pin: str) -> str:
    """Hash a caller PIN using a unique salt and stdlib PBKDF2-HMAC-SHA256."""
    normalized = validate_pin(pin)
    salt = secrets.token_bytes(PIN_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        normalized.encode("utf-8"),
        salt,
        PIN_ITERATIONS,
        dklen=PIN_DIGEST_BYTES,
    )
    return "$".join(
        (
            PIN_SCHEME,
            str(PIN_ITERATIONS),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(digest).decode("ascii"),
        )
    )


def verify_pin_hash(pin: str, encoded_hash: str | None) -> bool:
    """Verify a PIN in constant time; malformed hashes fail closed."""
    if not encoded_hash:
        return False
    try:
        normalized = validate_pin(pin)
        scheme, iterations_raw, salt_raw, expected_raw = encoded_hash.split("$", 3)
        if scheme != PIN_SCHEME:
            return False
        iterations = int(iterations_raw)
        if iterations < 100_000 or iterations > 2_000_000:
            return False
        salt = base64.urlsafe_b64decode(salt_raw.encode("ascii"))
        expected = base64.urlsafe_b64decode(expected_raw.encode("ascii"))
        if len(salt) < 16 or len(expected) != PIN_DIGEST_BYTES:
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            normalized.encode("utf-8"),
            salt,
            iterations,
            dklen=len(expected),
        )
    except (TypeError, ValueError, UnicodeError):
        return False
    return hmac.compare_digest(actual, expected)


def redact_pin_text(text: str) -> str:
    """Redact standalone 4-8 digit values without damaging longer order IDs."""
    return _SPOKEN_PIN_RE.sub("[REDACTED PIN]", text or "")


def redact_pin_data(value: Any) -> Any:
    """Recursively redact likely PINs from JSON-like evidence and trace payloads."""
    if isinstance(value, str):
        return redact_pin_text(value)
    if is_dataclass(value) and not isinstance(value, type):
        return redact_pin_data(asdict(value))
    if isinstance(value, dict):
        return {key: redact_pin_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_pin_data(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_pin_data(item) for item in value)
    return value


def redact_tool_calls_for_trace(tool_calls: Any) -> Any:
    """Redact provider tool-call payloads without breaking the calling protocol.

    ``tool_calls`` here is the raw, OpenAI-shaped structure returned by the LLM
    provider (``[{"id": ..., "type": "function", "function": {"name": ...,
    "arguments": "..."}}]``). A blanket `redact_pin_data` pass would also
    rewrite ``id``/``type``/``function.name`` if any of them happened to look
    like a 4-8 digit run. That redacted copy is replayed verbatim to the LLM
    provider on the next turn (via the assistant `ChatTurn.tool_calls`), and
    most OpenAI-compatible chat-completions APIs strictly match a later
    tool-role message's `tool_call_id` against it — a mismatch there can
    surface as a hard 400 error and abort a live call turn. Only
    `function.arguments` (a JSON string that can carry a caller-echoed PIN)
    is redacted; every identifier field is preserved byte-for-byte.
    """
    if not isinstance(tool_calls, list):
        return redact_pin_data(tool_calls)

    redacted: list[Any] = []
    for call in tool_calls:
        if not isinstance(call, dict):
            redacted.append(redact_pin_data(call))
            continue
        safe_call = dict(call)
        function = call.get("function")
        if isinstance(function, dict):
            safe_function = dict(function)
            if isinstance(function.get("arguments"), str):
                safe_function["arguments"] = redact_pin_text(function["arguments"])
            safe_call["function"] = safe_function
        redacted.append(safe_call)
    return redacted


def verify_legacy_pin(pin: str, plaintext_pin: str | None) -> bool:
    """Constant-time compatibility check for pre-Day-46 plaintext rows."""
    if not plaintext_pin:
        return False
    try:
        normalized = validate_pin(pin)
        expected = validate_pin(plaintext_pin)
    except ValueError:
        return False
    return hmac.compare_digest(normalized.encode("utf-8"), expected.encode("utf-8"))
