"""Tests for the AWS Lambda bridge that fronts Amazon Connect.

The Lambda lives in `deploy/aws/lambda_handler.py`, outside the API package,
because it is deployed on its own to AWS. It is still the single point every
phone call passes through: a fault here drops live calls, so it is tested here.

Every HTTP call is stubbed — these tests never touch the network.
"""

from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
from pathlib import Path

import pytest

# apps/api/tests/ -> repo root -> deploy/aws/lambda_handler.py
_LAMBDA_PATH = (
    Path(__file__).resolve().parents[3] / "deploy" / "aws" / "lambda_handler.py"
)


@pytest.fixture(scope="module")
def bridge():
    """Import the Lambda module by path (it is not an installed package)."""
    if not _LAMBDA_PATH.exists():  # pragma: no cover - repo layout guard
        pytest.skip(f"lambda_handler.py not found at {_LAMBDA_PATH}")
    spec = importlib.util.spec_from_file_location("voxflow_lambda_bridge", _LAMBDA_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def captured(monkeypatch, bridge):
    """Replace the outbound POST with a recorder returning a canned API reply."""
    calls: list[dict] = []

    def fake_post(url, payload, secret, path):
        calls.append({"url": url, "payload": payload, "secret": secret, "path": path})
        return {
            "agent_reply": "Your order was dispatched yesterday.",
            "escalate": False,
            "end_call": False,
            "language": "en",
        }

    monkeypatch.setattr(bridge, "_post_json", fake_post)
    return calls


def _event(user_text: str = "", **params) -> dict:
    """Build the event shape Amazon Connect actually sends."""
    parameters = {"user_text": user_text} if user_text else {}
    parameters.update(params)
    return {
        "Details": {
            "ContactData": {
                "ContactId": "cnt-lex-001",
                "CustomerEndpoint": {"Address": "+447700900123"},
                "SystemEndpoint": {"Address": "+442046404552"},
            },
            "Parameters": parameters,
        }
    }


# --------------------------------------------------------------- speech capture


def test_lex_transcript_is_forwarded_to_the_api(bridge, captured):
    """A real spoken transcript must reach /api/connect/turn unchanged."""
    spoken = "Has my order been dispatched yet?"

    result = bridge.lambda_handler(_event(spoken), None)

    assert len(captured) == 1, "expected exactly one API call"
    call = captured[0]
    assert call["path"] == "/api/connect/turn"
    assert call["payload"]["user_text"] == spoken
    assert call["payload"]["contact_id"] == "cnt-lex-001"
    assert call["payload"]["customer_phone"] == "+447700900123"
    assert call["payload"]["system_phone"] == "+442046404552"
    assert result["agent_reply"] == "Your order was dispatched yesterday."
    # Connect compares these against the string "true"/"false" in the flow.
    assert result["escalate"] == "false"
    assert result["end_call"] == "false"


def test_blank_transcript_reprompts_without_calling_the_api(bridge, captured):
    """Lex returning no transcript must re-prompt, not send empty text to the agent."""
    result = bridge.lambda_handler(_event(""), None)

    assert captured == [], "a blank transcript must not reach the agent"
    assert result["end_call"] == "false", "a blank turn must not hang up on the caller"
    assert result["escalate"] == "false"
    assert "help" in result["agent_reply"].lower()


def test_whitespace_only_transcript_is_treated_as_blank(bridge, captured):
    """Lex can return padding; whitespace is not a real utterance."""
    result = bridge.lambda_handler(_event("   "), None)

    assert captured == []
    assert result["end_call"] == "false"


# ------------------------------------------------------------ UK-English market


def test_reprompt_is_english_not_hindi(bridge, captured):
    """First market is the UK. The re-prompt must be English (ASCII, no Devanagari)."""
    reply = bridge.lambda_handler(_event(""), None)["agent_reply"]

    assert reply.isascii(), f"expected English re-prompt, got: {reply}"


def test_error_fallback_is_english_and_escalates(bridge, monkeypatch):
    """When the API is unreachable the caller hears English and a human is flagged."""

    def boom(*_args, **_kwargs):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(bridge, "_post_json", boom)

    result = bridge.lambda_handler(_event("Hello?"), None)

    # The flow must still get a speakable reply — never a raw 500.
    assert result["statusCode"] == 200
    assert result["agent_reply"].isascii(), result["agent_reply"]
    assert result["escalate"] == "true"
    assert result["end_call"] == "true"


def test_default_language_is_english(bridge, captured):
    """A new session defaults to 'en' so the agent's system prompt is English."""
    bridge.lambda_handler(_event("Hello"), None)

    assert captured[0]["payload"]["language"] == "en"


def test_explicit_language_parameter_wins(bridge, captured):
    """A flow that passes a language must override the default."""
    bridge.lambda_handler(_event("नमस्ते", language="hi"), None)

    assert captured[0]["payload"]["language"] == "hi"


def test_default_language_is_overridable_by_env(bridge, captured, monkeypatch):
    monkeypatch.setenv("VOXFLOW_DEFAULT_LANG", "hi")

    bridge.lambda_handler(_event("Hello"), None)

    assert captured[0]["payload"]["language"] == "hi"


# ------------------------------------------------------------------- API wiring


def test_api_url_env_var_overrides_the_default(bridge, captured, monkeypatch):
    monkeypatch.setenv("VOXFLOW_API_URL", "https://staging.example.com/")

    bridge.lambda_handler(_event("Hello"), None)

    # Trailing slash must be stripped so the path is not doubled up.
    assert captured[0]["url"] == "https://staging.example.com/api/connect/turn"


def test_default_api_url_is_not_a_sleeping_host(bridge, captured, monkeypatch):
    """Connect allows ~8s. A cold-starting free host blows that and drops the call."""
    monkeypatch.delenv("VOXFLOW_API_URL", raising=False)

    bridge.lambda_handler(_event("Hello"), None)

    assert "onrender.com" not in captured[0]["url"]


def test_end_action_finalises_the_session(bridge, captured):
    result = bridge.lambda_handler(_event(action="end", outcome="resolved"), None)

    assert captured[0]["path"] == "/api/connect/end"
    assert captured[0]["payload"] == {
        "contact_id": "cnt-lex-001",
        "outcome": "resolved",
    }
    assert result["status"] == "ended"


# -------------------------------------------------------------------- signature


def test_signature_matches_what_the_api_verifies(bridge, monkeypatch):
    """The HMAC must be over '{timestamp}:{path}' — the API rejects anything else."""
    secret = "shared-secret-abc123"
    timestamp = "1700000000.0"
    path = "/api/connect/turn"

    expected = hmac.new(
        secret.encode("utf-8"),
        f"{timestamp}:{path}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    assert bridge._sign_request(secret, timestamp, path) == expected


def test_secret_is_read_from_env_and_passed_to_the_signer(bridge, captured, monkeypatch):
    monkeypatch.setenv("VOXFLOW_SECRET", "from-env-secret")

    bridge.lambda_handler(_event("Hello"), None)

    assert captured[0]["secret"] == "from-env-secret"


def test_request_carries_signature_headers_when_a_secret_is_set(bridge, monkeypatch):
    """Guards the header names the API looks for: a rename here is a silent 403."""
    sent = {}

    class FakeResponse:
        def read(self):
            return json.dumps({"agent_reply": "ok"}).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    def fake_urlopen(req, timeout=None):
        sent["headers"] = {k.lower(): v for k, v in req.headers.items()}
        sent["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(bridge.urllib.request, "urlopen", fake_urlopen)

    bridge._post_json(
        "https://example.com/api/connect/turn",
        {"user_text": "hi"},
        "a-secret",
        "/api/connect/turn",
    )

    assert "x-voxflow-signature" in sent["headers"]
    assert "x-voxflow-timestamp" in sent["headers"]
    # Connect's own limit is ~8s; the HTTP call must not outlive it.
    assert sent["timeout"] <= 8
