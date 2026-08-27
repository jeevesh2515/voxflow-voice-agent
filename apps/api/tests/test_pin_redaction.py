"""Regression coverage for proactive caller-PIN redaction and safe seed defaults."""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import asdict
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

from voxflow_api.agent import runner as runner_module
from voxflow_api.agent.runner import (
    AgentRunner,
    AgentTurnResult,
    _redacted_trace_inputs,
    _redacted_trace_outputs,
)
from voxflow_api.db import Call, Supplier, Tenant, reset_db, session_scope
from voxflow_api.llm.base import ChatTurn, LLMProvider, LLMResponse
from voxflow_api.schemas import CallTurn
from voxflow_api.seed import seed
from voxflow_api.services.pin_security import (
    hash_pin,
    redact_pin_data,
    redact_pin_text,
    redact_tool_calls_for_trace,
    verify_pin_hash,
)
from voxflow_api.voice import pipeline as pipeline_module
from voxflow_api.voice.pipeline import CallSession, VoicePipeline, _snapshot_session


PIN = "4321"
LONG_ORDER_ID = "PO-1717000000-001"


class SequenceLLM(LLMProvider):
    name = "test"
    model = "test-model"

    def __init__(self, responses: list[LLMResponse]) -> None:
        self.responses = responses
        self.messages_seen: list[list[ChatTurn]] = []

    async def chat(
        self,
        messages: list[ChatTurn],
        *,
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        del tools, temperature, max_tokens
        self.messages_seen.append(list(messages))
        return self.responses.pop(0)

    async def health(self) -> bool:
        return True


class CapturingLog:
    def __init__(self) -> None:
        self.records: list[tuple[str, str, dict[str, Any]]] = []

    def info(self, event: str, **kwargs: Any) -> None:
        self.records.append(("info", event, kwargs))

    def warning(self, event: str, **kwargs: Any) -> None:
        self.records.append(("warning", event, kwargs))


def _serialized(value: Any) -> str:
    return json.dumps(value, default=str, sort_keys=True)


def _turn_payloads(turns: list[CallTurn]) -> list[dict[str, Any]]:
    return [turn.model_dump(mode="json") for turn in turns]


def test_bounded_matcher_and_recursive_trace_redaction_preserve_long_order_ids() -> None:
    raw = f"PINs 1234 and 12345678; order {LONG_ORDER_ID}; long number 123456789."
    redacted = redact_pin_text(raw)

    assert redacted.count("[REDACTED PIN]") == 2
    assert "PINs 1234" not in redacted
    assert "and 12345678" not in redacted
    assert LONG_ORDER_ID in redacted
    assert "123456789" in redacted

    nested = redact_pin_data({"reply": f"Use {PIN}", "actions": [{"note": f"{PIN} for {LONG_ORDER_ID}"}]})
    assert PIN not in _serialized(nested)
    assert LONG_ORDER_ID in _serialized(nested)

    session = CallSession(call_id="trace-call", tenant_id="varun")
    trace_input = _redacted_trace_inputs({"session": session, "user_text": f"My PIN is {PIN}"})
    trace_output = _redacted_trace_outputs(
        {
            "reply": f"I heard {PIN}",
            "actions": [{"name": "note", "result": f"{PIN} for {LONG_ORDER_ID}"}],
        }
    )
    assert PIN not in _serialized(trace_input)
    assert PIN not in _serialized(trace_output)
    assert LONG_ORDER_ID in _serialized(trace_output)

    shared_result = AgentTurnResult(
        reply=f"Connect reply {PIN} for {LONG_ORDER_ID}",
        actions=[{"name": "capture_note", "result": f"PIN {PIN}"}],
        tool_calls=[{"name": "capture_note", "args": {"note": f"PIN {PIN}"}}],
    )
    assert PIN not in _serialized(asdict(shared_result))
    assert LONG_ORDER_ID in _serialized(asdict(shared_result))


def test_runner_redacts_without_verify_pin_and_keeps_raw_value_only_for_execution(monkeypatch) -> None:
    tool_call = {
        "id": "tool-call-1",
        "type": "function",
        "function": {
            "name": "capture_note",
            "arguments": json.dumps({"note": f"Caller said PIN {PIN} for {LONG_ORDER_ID}"}),
        },
    }
    llm = SequenceLLM(
        [
            LLMResponse(content=f"Working with {PIN}", tool_calls=[tool_call], provider="test", model="test"),
            LLMResponse(content=f"Confirmed {PIN} for {LONG_ORDER_ID}", provider="test", model="test"),
        ]
    )
    executed: dict[str, Any] = {}

    async def fake_execute(name: str, args: dict[str, Any], session: CallSession) -> dict[str, Any]:
        del session
        executed.update({"name": name, "args": args})
        return {"ok": True, "message": f"Stored {PIN} for {LONG_ORDER_ID}"}

    captured_log = CapturingLog()
    monkeypatch.setattr(runner_module, "execute_tool", fake_execute)
    monkeypatch.setattr(runner_module, "log", captured_log)

    session = CallSession(call_id="runner-redaction", tenant_id="varun")
    session.transcript.append(
        CallTurn(
            role="caller",
            text=f"My PIN is {PIN}; check {LONG_ORDER_ID}",
            at=datetime.now(timezone.utc),
        )
    )
    runner = AgentRunner(llm=llm)
    runner._resolve_tenant_prompt = lambda tenant_id, session_language=None: "test prompt"  # type: ignore[method-assign]

    result = asyncio.run(runner.handle_turn(session, session.transcript[-1].text))

    assert executed["args"]["note"].startswith(f"Caller said PIN {PIN}")
    assert PIN not in _serialized(asdict(result))
    assert PIN not in _serialized(_turn_payloads(session.transcript))
    assert PIN not in _serialized(captured_log.records)
    assert LONG_ORDER_ID in _serialized(asdict(result))
    assert LONG_ORDER_ID in _serialized(_turn_payloads(session.transcript))
    assert all(action["name"] != "verify_pin" for action in result.actions)


def test_audio_commit_redacts_result_transcript_actions_and_tts_without_pin_tool(monkeypatch) -> None:
    class FakeSTT:
        def transcribe_pcm(self, pcm: Any, sample_rate: int) -> Any:
            del pcm, sample_rate
            return SimpleNamespace(
                text=f"My PIN is 7654 for {LONG_ORDER_ID}",
                confidence=0.99,
                language="en",
            )

    class FakeAgent:
        async def handle_turn(self, session: CallSession, user_text: str) -> Any:
            assert "7654" in user_text
            return SimpleNamespace(
                reply=f"I heard 7654 for {LONG_ORDER_ID}",
                actions=[{"name": "capture_note", "args": {"note": "PIN 7654"}}],
            )

    class FakeTTS:
        def __init__(self) -> None:
            self.text = ""

        async def synth(self, text: str, lang_hint: str) -> Any:
            del lang_hint
            self.text = text
            return SimpleNamespace(audio_bytes=b"audio", mime="audio/mpeg")

    monkeypatch.setattr(pipeline_module, "_snapshot_session", lambda session: None)
    pipeline = object.__new__(VoicePipeline)
    pipeline.stt = FakeSTT()
    pipeline.agent = FakeAgent()
    pipeline.tts = FakeTTS()
    session = CallSession(call_id="audio-redaction", tenant_id="varun")
    session.append_pcm(b"\x00\x00" * 20)

    result = asyncio.run(pipeline.commit_audio(session))

    evidence = _serialized(
        {
            "result": result,
            "transcript": _turn_payloads(session.transcript),
            "actions": session.actions,
            "tts": pipeline.tts.text,
        }
    )
    assert "7654" not in evidence
    assert LONG_ORDER_ID in evidence
    assert all(action["name"] != "verify_pin" for action in result["actions"])


def test_snapshot_database_and_sheet_fallbacks_are_always_redacted(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(pipeline_module, "_sessions_dir", lambda: str(tmp_path))
    snapshot_session = CallSession(call_id="pin-snapshot", tenant_id="pin-redaction-tenant")
    snapshot_session.transcript = [
        CallTurn(role="caller", text=f"PIN 2468 for {LONG_ORDER_ID}", at=datetime.now(timezone.utc)),
        CallTurn(role="agent", text=f"I heard 2468 for {LONG_ORDER_ID}", at=datetime.now(timezone.utc)),
    ]
    snapshot_session.actions = [{"name": "capture_note", "result": "PIN 2468"}]

    _snapshot_session(snapshot_session)

    snapshot_text = (tmp_path / "pin-snapshot.json").read_text(encoding="utf-8")
    assert "2468" not in snapshot_text
    assert LONG_ORDER_ID in snapshot_text

    tenant_id = "pin-redaction-tenant"
    with session_scope() as db:
        if db.get(Tenant, tenant_id) is None:
            db.add(Tenant(id=tenant_id, name="PIN Redaction Tenant"))

    persist_session = CallSession(
        call_id="pin-redaction-persist",
        tenant_id=tenant_id,
        ended_at=time.time(),
        reason="Caller supplied PIN 6789",
        solution=f"Checked 6789 against {LONG_ORDER_ID}",
        related_order=LONG_ORDER_ID,
    )
    persist_session.transcript = [
        CallTurn(role="caller", text=f"PIN 6789 for {LONG_ORDER_ID}", at=datetime.now(timezone.utc)),
        CallTurn(role="agent", text=f"Confirmed 6789 for {LONG_ORDER_ID}", at=datetime.now(timezone.utc)),
    ]
    persist_session.actions = [{"name": "capture_note", "args": {"note": "PIN 6789"}}]
    pipeline = object.__new__(VoicePipeline)

    asyncio.run(pipeline._persist(persist_session))

    with session_scope() as db:
        row = db.get(Call, persist_session.call_id)
        assert row is not None
        persisted = _serialized(
            {
                "transcript": row.transcript_json,
                "actions": row.actions_json,
                "reason": row.reason,
                "solution": row.solution,
            }
        )
    assert "6789" not in persisted
    assert LONG_ORDER_ID in persisted

    sheet_session = CallSession(call_id="sheet-fallback", tenant_id=tenant_id)
    sheet_session.transcript = [
        CallTurn(role="caller", text=f"Where is 8765 for {LONG_ORDER_ID}?", at=datetime.now(timezone.utc)),
        CallTurn(role="agent", text=f"8765 is linked to {LONG_ORDER_ID}", at=datetime.now(timezone.utc)),
    ]
    sheet_row = pipeline.sheet_row_for(sheet_session)
    assert "8765" not in _serialized(sheet_row)
    assert LONG_ORDER_ID in _serialized(sheet_row)
    assert sheet_row["timestamp"][:4].isdigit()


def test_tool_call_ids_survive_redaction_while_arguments_are_scrubbed() -> None:
    """A blanket redaction pass over a raw provider tool-call structure must
    not rewrite `id`/`type`/`function.name` — those are replayed verbatim to
    the LLM on the next turn, and most OpenAI-compatible APIs strictly match
    a later tool-role message's `tool_call_id` against them. Only
    `function.arguments` (which can carry a caller-echoed PIN) is redacted.
    """
    numeric_looking_id = "call_12345678"  # realistic-shaped provider tool-call id
    tool_calls = [
        {
            "id": numeric_looking_id,
            "type": "function",
            "function": {
                "name": "verify_pin",
                "arguments": json.dumps({"pin": PIN}),
            },
        }
    ]

    redacted = redact_tool_calls_for_trace(tool_calls)

    assert redacted[0]["id"] == numeric_looking_id, "tool_call_id must round-trip unchanged"
    assert redacted[0]["type"] == "function"
    assert redacted[0]["function"]["name"] == "verify_pin"
    assert PIN not in redacted[0]["function"]["arguments"]
    assert "[REDACTED PIN]" in redacted[0]["function"]["arguments"]


def test_runner_preserves_numeric_tool_call_id_across_turns(monkeypatch) -> None:
    """End-to-end: a numeric-looking tool_call id from the provider must match
    between the replayed assistant message and the following tool message,
    even though the call's PIN argument gets redacted along the way."""
    numeric_looking_id = "87654321"
    tool_call = {
        "id": numeric_looking_id,
        "type": "function",
        "function": {
            "name": "verify_pin",
            "arguments": json.dumps({"pin": PIN}),
        },
    }
    llm = SequenceLLM(
        [
            LLMResponse(content="", tool_calls=[tool_call], provider="test", model="test"),
            LLMResponse(content="Done", provider="test", model="test"),
        ]
    )

    async def fake_execute(name: str, args: dict[str, Any], session: CallSession) -> dict[str, Any]:
        del name, args, session
        return {"verified": True}

    monkeypatch.setattr(runner_module, "execute_tool", fake_execute)

    session = CallSession(call_id="runner-tool-id", tenant_id="varun")
    runner = AgentRunner(llm=llm)
    runner._resolve_tenant_prompt = lambda tenant_id, session_language=None: "test prompt"  # type: ignore[method-assign]

    asyncio.run(runner.handle_turn(session, "verify my pin"))

    second_call_messages = llm.messages_seen[1]
    assistant_message = next(m for m in second_call_messages if m.role == "assistant")
    tool_message = next(m for m in second_call_messages if m.role == "tool")
    assert assistant_message.tool_calls[0]["id"] == numeric_looking_id
    assert tool_message.tool_call_id == numeric_looking_id


def test_caller_phone_survives_snapshot_and_persist_unmangled(monkeypatch, tmp_path) -> None:
    """caller_phone is structured telephony metadata, not free-text caller
    speech. The 4-8 digit PIN redaction regex must not be applied to it —
    doing so replaces a real phone number's digit groups with placeholder
    text and corrupts the stored/logged number."""
    monkeypatch.setattr(pipeline_module, "_sessions_dir", lambda: str(tmp_path))
    formatted_phone = "+44 7700 900123"

    snapshot_session = CallSession(
        call_id="pin-phone-snapshot",
        tenant_id="pin-redaction-tenant",
        caller_phone=formatted_phone,
    )
    _snapshot_session(snapshot_session)
    snapshot_text = (tmp_path / "pin-phone-snapshot.json").read_text(encoding="utf-8")
    assert formatted_phone in snapshot_text
    assert "[REDACTED PIN]" not in snapshot_text

    tenant_id = "pin-redaction-tenant"
    with session_scope() as db:
        if db.get(Tenant, tenant_id) is None:
            db.add(Tenant(id=tenant_id, name="PIN Redaction Tenant"))

    persist_session = CallSession(
        call_id="pin-phone-persist",
        tenant_id=tenant_id,
        caller_phone=formatted_phone,
        ended_at=time.time(),
    )
    pipeline = object.__new__(VoicePipeline)
    asyncio.run(pipeline._persist(persist_session))

    with session_scope() as db:
        row = db.get(Call, persist_session.call_id)
        assert row is not None
        assert row.caller_phone == formatted_phone

    captured_log = CapturingLog()
    monkeypatch.setattr(pipeline_module, "log", captured_log)
    bare_pipeline = object.__new__(pipeline_module.VoicePipeline)
    bare_pipeline._sessions = {}
    bare_pipeline.start_session(caller_phone=formatted_phone, tenant_id=tenant_id)
    logged_phones = [
        kwargs.get("caller_phone")
        for _, event, kwargs in captured_log.records
        if event == "call.started"
    ]
    assert formatted_phone in logged_phones


def test_websocket_text_response_is_redacted_without_verify_pin(monkeypatch) -> None:
    from voxflow_api.routes import ws as ws_module

    class FakeTTS:
        async def synth(self, text: str, lang_hint: str) -> Any:
            del lang_hint
            assert PIN not in text
            return SimpleNamespace(audio_bytes=b"audio", mime="audio/mpeg")

    class FakePipeline:
        def __init__(self) -> None:
            self.tts = FakeTTS()
            self.session: CallSession | None = None

        def start_session(self, **kwargs: Any) -> CallSession:
            self.session = CallSession(
                call_id="ws-redaction",
                tenant_id=kwargs["tenant_id"],
                language=kwargs.get("language") or "en",
            )
            return self.session

        async def end_session(self, call_id: str, outcome: str) -> CallSession | None:
            del call_id, outcome
            return self.session

    class FakeWebSocket:
        def __init__(self) -> None:
            self.incoming = [
                {"type": "start", "language": "en"},
                {"type": "text", "text": f"PIN {PIN} for {LONG_ORDER_ID}"},
                {"type": "end"},
            ]
            self.sent: list[dict[str, Any]] = []

        async def accept(self) -> None:
            return None

        async def receive_text(self) -> str:
            return json.dumps(self.incoming.pop(0))

        async def send_json(self, payload: dict[str, Any]) -> None:
            self.sent.append(payload)

    async def fake_turn(self: AgentRunner, session: CallSession, user_text: str) -> Any:
        del self, session
        assert PIN in user_text
        return SimpleNamespace(
            reply=f"I heard {PIN} for {LONG_ORDER_ID}",
            actions=[{"name": "capture_note", "result": f"PIN {PIN}"}],
        )

    fake_pipeline = FakePipeline()
    fake_ws = FakeWebSocket()
    monkeypatch.setattr(ws_module, "get_pipeline", lambda: fake_pipeline)
    monkeypatch.setattr(AgentRunner, "handle_turn", fake_turn)

    asyncio.run(ws_module.call_socket(fake_ws))

    turn = next(payload for payload in fake_ws.sent if payload.get("type") == "turn")
    assert PIN not in _serialized(turn)
    assert LONG_ORDER_ID in _serialized(turn)
    assert fake_pipeline.session is not None
    assert PIN not in _serialized(_turn_payloads(fake_pipeline.session.transcript))


def test_http_agent_and_chat_responses_are_redacted_without_verify_pin(monkeypatch) -> None:
    from voxflow_api import main as main_module

    class FakePipeline:
        def __init__(self) -> None:
            self._sessions: dict[str, CallSession] = {}
            self.persisted: CallSession | None = None

        async def recover_orphaned_sessions(self) -> int:
            return 0

        def start_session(self, **kwargs: Any) -> CallSession:
            session = CallSession(
                call_id="http-redaction",
                tenant_id="varun",
                language=kwargs.get("language") or "en",
                caller_phone=kwargs.get("caller_phone", ""),
                caller_name=kwargs.get("caller_name", ""),
            )
            self._sessions[session.call_id] = session
            return session

        async def _persist(self, session: CallSession) -> None:
            self.persisted = session

    class FakeChatLLM:
        async def chat(self, messages: list[ChatTurn], **kwargs: Any) -> LLMResponse:
            del messages, kwargs
            return LLMResponse(
                content=f"Chat reply contains {PIN} for {LONG_ORDER_ID}",
                tool_calls=[{"function": {"arguments": json.dumps({"note": f"PIN {PIN}"})}}],
                provider="test",
                model="test",
            )

    async def fake_turn(self: AgentRunner, session: CallSession, user_text: str) -> Any:
        del self, session
        assert PIN in user_text
        return SimpleNamespace(
            reply=f"Agent reply contains {PIN} for {LONG_ORDER_ID}",
            actions=[{"name": "capture_note", "result": f"PIN {PIN}"}],
        )

    fake_pipeline = FakePipeline()
    monkeypatch.setattr(main_module, "get_pipeline", lambda: fake_pipeline)
    monkeypatch.setattr(main_module, "get_llm", lambda: FakeChatLLM())
    monkeypatch.setattr(AgentRunner, "handle_turn", fake_turn)

    with TestClient(main_module.create_app()) as client:
        agent_response = client.post("/agent/run", json={"text": f"PIN {PIN} for {LONG_ORDER_ID}"})
        chat_response = client.post(
            "/chat",
            json={"messages": [{"role": "user", "content": f"PIN {PIN}"}]},
        )

    assert agent_response.status_code == 200
    assert chat_response.status_code == 200
    assert PIN not in agent_response.text
    assert PIN not in chat_response.text
    assert LONG_ORDER_ID in agent_response.text
    assert LONG_ORDER_ID in chat_response.text
    assert fake_pipeline.persisted is not None
    assert PIN not in _serialized(_turn_payloads(fake_pipeline.persisted.transcript))
    assert PIN not in _serialized(fake_pipeline.persisted.actions)


def test_normal_seed_contacts_have_no_pin_but_fixtures_can_set_one_explicitly() -> None:
    from voxflow_api.main import create_app

    reset_db()
    seed(reset=True)

    with session_scope() as db:
        contacts = db.query(Supplier).all()
        assert contacts
        assert all(contact.auth_pin is None for contact in contacts)
        assert all(contact.auth_pin_hash is None for contact in contacts)
        assert all(contact.pin_updated_at is None for contact in contacts)
        assert all(contact.pin_configured is False for contact in contacts)

    client = TestClient(create_app())
    response = client.get("/api/admin/tenants/varun/caller-pins")
    client.close()
    assert response.status_code == 200
    assert response.json()
    assert all(item["pin_configured"] is False for item in response.json())

    fixture_hash = hash_pin("8642")
    fixture_contact = Supplier(
        id="fixture-pin-contact",
        tenant_id="varun",
        name="Explicit Fixture Contact",
        auth_pin=None,
        auth_pin_hash=fixture_hash,
    )
    assert fixture_contact.pin_configured is True
    assert verify_pin_hash("8642", fixture_hash)
