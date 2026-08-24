"""Day 42 — durable call logging: one Postgres row + one Google Sheet row.

Contract under test:
* The Postgres `calls` row is the source of truth and persists on end_session.
* The Sheets mirror is per-tenant gated, off the request path, and idempotent:
  exactly one Sheet row per call even if /api/connect/end is retried.
* A Sheets failure must never fail the call or delay the caller; the Postgres
  row still lands with sheet_synced=0.
"""

from __future__ import annotations

import asyncio
import time

import pytest

from voxflow_api.config import get_settings
from voxflow_api.db import Call, Tenant, init_db, session_scope
from voxflow_api.integrations import gsheets
from voxflow_api.integrations.gsheets import CALL_LOG_HEADERS
from voxflow_api.schemas import CallTurn
from voxflow_api.voice.pipeline import VoicePipeline

TENANT = "mirror-tenant"


@pytest.fixture(autouse=True)
def _reset_pipeline_state():
    """Class-level inflight/background sets must not leak across tests."""
    VoicePipeline._sheet_inflight.clear()
    VoicePipeline._background_tasks.clear()
    yield
    VoicePipeline._sheet_inflight.clear()
    for task in list(VoicePipeline._background_tasks):
        task.cancel()


@pytest.fixture
def pipeline():
    p = VoicePipeline.__new__(VoicePipeline)  # skip __init__ (loads STT/LLM)
    p._sessions = {}
    return p


@pytest.fixture
def session():
    from voxflow_api.voice.pipeline import CallSession

    s = CallSession(call_id="day42-call-1", tenant_id=TENANT)
    s.caller_phone = "+441234567890"
    s.caller_name = "Test Caller"
    s.company_name = "Acme Ltd"
    s.verified = True
    s.resolution_status = "resolved"
    s.reason = "Where is my order?"
    s.solution = "Out for delivery today"
    s.turn_latencies = [120.0, 180.5]
    s.transcript.append(CallTurn(role="caller", text="Where is my order?", at=time.time()))
    s.transcript.append(CallTurn(role="agent", text="Out for delivery today", at=time.time()))
    return s


class _FakeSheets:
    def __init__(self, *, ok: bool = True, delay: float = 0.0, raise_exc: Exception | None = None):
        self.ok = ok
        self.delay = delay
        self.raise_exc = raise_exc
        self.calls: list[dict] = []

    def is_configured(self) -> bool:
        return True

    async def append_call_outcome(self, row, queue_on_failure=True):
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.raise_exc:
            raise self.raise_exc
        self.calls.append(row)
        return {"ok": self.ok, "tab": "Call Log"} if self.ok else {"ok": False, "reason": "http_500"}


def _seed_tenant():
    init_db()
    with session_scope() as db:
        if not db.get(Tenant, TENANT):
            db.add(Tenant(id=TENANT, name="Mirror Tenant"))


# --------------------------------------------------------------------- columns


def test_new_columns_are_appended_not_reordered():
    """Existing consumers filter by position — new columns go at the END."""
    assert CALL_LOG_HEADERS[:15] == [
        "Timestamp (IST)",
        "Call ID",
        "Caller Phone",
        "Caller Name",
        "Company",
        "Identity Verified",
        "Language",
        "Reason for Call",
        "Solution Given",
        "Resolution Status",
        "Satisfaction",
        "Follow-up Required",
        "Escalated",
        "Duration (sec)",
        "Related Order",
    ]
    assert CALL_LOG_HEADERS[15:] == ["Tenant", "Question", "Answer", "Turn Latency (ms)"]


def test_append_call_outcome_maps_day42_columns():
    captured = {}

    class _Capture(gsheets.GoogleSheetsClient):
        async def append_row(self, values, tab=None, headers=None):
            captured["values"] = values
            captured["headers"] = headers
            return {"ok": True}

    client = _Capture()
    row = {
        "timestamp": "2026-08-24 10:00:00",
        "call_id": "c1",
        "caller_phone": "+44",
        "caller_name": "A",
        "company": "B",
        "verified": True,
        "language": "en",
        "reason": "r",
        "solution": "s",
        "resolution_status": "resolved",
        "satisfaction": "happy",
        "follow_up_required": False,
        "escalated": False,
        "duration_sec": 60,
        "related_order": "PO-1",
        "tenant": "varun",
        "question": "q",
        "answer": "a",
        "turn_latency_ms": 150,
    }
    asyncio.run(client.append_call_outcome(row))
    assert len(captured["values"]) == len(CALL_LOG_HEADERS)
    assert captured["values"][-4:] == ["varun", "q", "a", 150]


# ----------------------------------------------------------------- row builder


def test_sheet_row_contains_question_answer_tenant_latency(pipeline, session):
    row = pipeline.sheet_row_for(session)
    assert row["tenant"] == TENANT
    assert row["question"] == "Where is my order?"
    assert row["answer"] == "Out for delivery today"
    assert row["turn_latency_ms"] == 150  # mean of [120, 180.5]
    assert row["call_id"] == "day42-call-1"


def test_sheet_row_falls_back_to_transcript_when_outcome_missing(pipeline):
    from voxflow_api.voice.pipeline import CallSession

    s = CallSession(call_id="day42-bare", tenant_id=TENANT)
    s.transcript.append(CallTurn(role="caller", text="hello?", at=time.time()))
    s.transcript.append(CallTurn(role="agent", text="hi, how can I help?", at=time.time()))
    row = pipeline.sheet_row_for(s)
    assert row["question"] == "hello?"
    assert row["answer"] == "hi, how can I help?"
    assert row["turn_latency_ms"] == ""


# ----------------------------------------------------------------------- gate


def test_gate_requires_explicit_tenant_allow_list(pipeline, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "sheets_call_log_tenants", TENANT, raising=False)
    fake = _FakeSheets()

    original = gsheets.get_sheets_client
    gsheets.get_sheets_client = lambda: fake  # type: ignore[assignment]
    try:
        assert pipeline.sheet_mirror_enabled(TENANT) is True
        assert pipeline.sheet_mirror_enabled("other-tenant") is False
        monkeypatch.setattr(s, "sheets_call_log_tenants", "", raising=False)
        assert pipeline.sheet_mirror_enabled(TENANT) is False
    finally:
        gsheets.get_sheets_client = original  # type: ignore[assignment]


# ------------------------------------------------------------- mirror behavior


def _call_row(call_id: str) -> Call | None:
    with session_scope() as db:
        return db.get(Call, call_id)


def _live(pipeline: VoicePipeline, session) -> None:
    """Register the session as an active live call (end_session pops it)."""
    pipeline._sessions[session.call_id] = session


def test_end_session_mirrors_off_the_request_path_and_marks_synced(pipeline, session, monkeypatch):
    _seed_tenant()
    s = get_settings()
    monkeypatch.setattr(s, "sheets_call_log_tenants", TENANT, raising=False)
    fake = _FakeSheets(delay=1.5)

    async def scenario():
        _live(pipeline, session)
        t0 = time.perf_counter()
        ended = await pipeline.end_session(session.call_id, outcome="resolved")
        elapsed = time.perf_counter() - t0
        # /end returned long before the slow Sheets write finished...
        assert elapsed < 1.0, f"end_session blocked {elapsed:.2f}s on Sheets"
        await pipeline.drain_background_tasks(timeout=5)
        return ended

    original = gsheets.get_sheets_client
    gsheets.get_sheets_client = lambda: fake  # type: ignore[assignment]
    try:
        ended = asyncio.run(scenario())
    finally:
        gsheets.get_sheets_client = original  # type: ignore[assignment]

    assert ended is not None
    # ...and exactly one Sheet row was written afterwards.
    assert len(fake.calls) == 1
    assert fake.calls[0]["call_id"] == session.call_id
    row = _call_row(session.call_id)
    assert row is not None and row.sheet_synced == 1
    assert row.avg_turn_latency_ms == 150


def test_retrying_end_does_not_double_write(pipeline, session, monkeypatch):
    _seed_tenant()
    s = get_settings()
    monkeypatch.setattr(s, "sheets_call_log_tenants", TENANT, raising=False)
    fake = _FakeSheets()

    async def scenario():
        _live(pipeline, session)
        await pipeline.end_session(session.call_id, outcome="resolved")
        await pipeline.drain_background_tasks(timeout=5)
        # Lambda retry after the session was popped: no second schedule/write.
        return await pipeline.end_session(session.call_id, outcome="resolved")

    original = gsheets.get_sheets_client
    gsheets.get_sheets_client = lambda: fake  # type: ignore[assignment]
    try:
        second = asyncio.run(scenario())
    finally:
        gsheets.get_sheets_client = original  # type: ignore[assignment]

    assert second is None
    assert len(fake.calls) == 1


def test_sheets_failure_keeps_postgres_row_and_never_raises(pipeline, session, monkeypatch):
    _seed_tenant()
    s = get_settings()
    monkeypatch.setattr(s, "sheets_call_log_tenants", TENANT, raising=False)
    fake = _FakeSheets(raise_exc=RuntimeError("google down"))

    async def scenario():
        _live(pipeline, session)
        await pipeline.end_session(session.call_id, outcome="resolved")
        await pipeline.drain_background_tasks(timeout=5)

    original = gsheets.get_sheets_client
    gsheets.get_sheets_client = lambda: fake  # type: ignore[assignment]
    try:
        asyncio.run(scenario())
    finally:
        gsheets.get_sheets_client = original  # type: ignore[assignment]

    row = _call_row(session.call_id)
    assert row is not None, "Postgres row must land even when Sheets fails"
    assert row.sheet_synced == 0


def test_db_guard_skips_already_synced_calls(pipeline, session, monkeypatch):
    """Crash-restart safety: sheet_synced=1 in Postgres blocks a re-mirror."""
    _seed_tenant()
    s = get_settings()
    monkeypatch.setattr(s, "sheets_call_log_tenants", TENANT, raising=False)
    asyncio.run(pipeline._persist(session))
    with session_scope() as db:
        db.get(Call, session.call_id).sheet_synced = 1

    fake = _FakeSheets()
    original = gsheets.get_sheets_client
    gsheets.get_sheets_client = lambda: fake  # type: ignore[assignment]
    try:
        asyncio.run(pipeline._mirror_sheet(session))
    finally:
        gsheets.get_sheets_client = original  # type: ignore[assignment]

    assert fake.calls == []
