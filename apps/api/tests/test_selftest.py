"""Tests for the deployment self-test.

The self-test is the thing you run when a deployment is misbehaving, so it has
to be trustworthy: it must never crash, must fail loudly for the right reasons,
and must not report success when something is actually broken.

Network-dependent checks (LLM, TTS, live STT) are covered by the self-test
running against a real deployment. What's tested here is the logic that decides
PASS/FAIL/SKIP, and the audio-decode path — using the checked-in MP3 fixture so
no network is needed.
"""

from __future__ import annotations

import asyncio
import base64

import pytest

from voxflow_api import selftest
from voxflow_api.selftest import FAIL, PASS, SKIP, WARN

from .test_twilio import _MP3_FIXTURE_B64


# ── config ──────────────────────────────────────────────────────────────────


def test_config_check_passes_with_a_usable_configuration(monkeypatch):
    from voxflow_api.config import get_settings

    s = get_settings()
    monkeypatch.setattr(s, "database_url", "postgresql://u:p@db.example.com:5432/postgres", raising=False)
    monkeypatch.setattr(s, "groq_api_key", "gsk_test", raising=False)

    status, detail, _ = asyncio.run(selftest.check_config())
    assert status == PASS
    assert "postgres" in detail


def test_config_check_fails_when_database_url_is_empty(monkeypatch):
    from voxflow_api.config import get_settings

    s = get_settings()
    monkeypatch.setattr(s, "database_url", "", raising=False)

    status, detail, hint = asyncio.run(selftest.check_config())
    assert status == FAIL
    assert "DATABASE_URL is empty" in detail
    assert hint  # must tell the user what to do


def test_config_check_fails_when_groq_selected_without_a_key(monkeypatch):
    from voxflow_api.config import get_settings

    s = get_settings()
    monkeypatch.setattr(s, "database_url", "postgresql://u:p@h:5432/d", raising=False)
    monkeypatch.setattr(s, "stt_provider", "groq", raising=False)
    monkeypatch.setattr(s, "groq_api_key", "", raising=False)

    status, detail, _ = asyncio.run(selftest.check_config())
    assert status == FAIL
    assert "GROQ_API_KEY" in detail


# ── database / migration detection ─────────────────────────────────────────


def test_database_check_passes_on_a_fully_migrated_schema():
    """init_db() builds from the ORM, which includes the migration columns."""
    from voxflow_api.db import init_db

    init_db()
    status, detail, _ = asyncio.run(selftest.check_database())
    assert status == PASS, detail
    assert "migration 001" in detail


def test_database_check_detects_a_missing_migration(monkeypatch):
    """The most valuable check in the suite.

    Running schema.md but forgetting migrations/001 leaves every table present
    and every new column absent. The app then fails at runtime with an opaque
    SQL error on the first call. This must be caught up front and named.
    """
    from voxflow_api.db import init_db

    init_db()

    # Pretend `orders` never received its PO-signing columns.
    original = dict(selftest._MIGRATION_COLUMNS)
    monkeypatch.setitem(selftest._MIGRATION_COLUMNS, "orders", ["a_column_that_does_not_exist"])
    try:
        status, detail, hint = asyncio.run(selftest.check_database())
    finally:
        selftest._MIGRATION_COLUMNS.clear()
        selftest._MIGRATION_COLUMNS.update(original)

    assert status == FAIL
    assert "migration columns are missing" in detail
    assert "001_customer_support_flow.sql" in hint


def test_database_check_names_missing_tables(monkeypatch):
    from voxflow_api.db import init_db

    init_db()
    monkeypatch.setattr(
        selftest, "_EXPECTED_TABLES", selftest._EXPECTED_TABLES + ["a_table_that_is_not_there"]
    )
    status, detail, hint = asyncio.run(selftest.check_database())
    assert status == FAIL
    assert "a_table_that_is_not_there" in detail
    assert "schema.md" in hint


# ── audio path (no network — uses the MP3 fixture) ─────────────────────────


def test_codec_check_passes_on_real_mp3_audio():
    """mp3 → pcm8k → mulaw → pcm → 16k, asserting the invariants hold."""
    state = {"mp3": base64.b64decode(_MP3_FIXTURE_B64)}
    status, detail, _ = asyncio.run(selftest.check_codecs(state))
    assert status == PASS, detail
    assert "consistent" in detail
    # It must hand decoded 16kHz audio on to the STT stage.
    assert state.get("pcm16k")
    assert len(state["pcm16k"]) % 2 == 0


def test_codec_check_skips_cleanly_when_tts_produced_nothing():
    """A failed TTS stage must cascade to SKIP, not an exception."""
    status, detail, _ = asyncio.run(selftest.check_codecs({}))
    assert status == SKIP
    assert detail


def test_stt_check_skips_cleanly_without_audio():
    status, _, _ = asyncio.run(selftest.check_stt({}))
    assert status == SKIP


# ── Sheets ─────────────────────────────────────────────────────────────────


def test_sheets_check_skips_when_disabled(monkeypatch):
    """Deferring Sheets is a supported state and must not read as a failure."""
    from voxflow_api.config import get_settings

    monkeypatch.setattr(get_settings(), "sheets_enabled", False, raising=False)
    status, detail, _ = asyncio.run(selftest.check_sheets())
    assert status == SKIP
    assert "Postgres" in detail  # reassures the user nothing is lost


def test_sheets_check_fails_when_enabled_but_unconfigured(monkeypatch):
    from voxflow_api.config import get_settings

    s = get_settings()
    monkeypatch.setattr(s, "sheets_enabled", True, raising=False)
    monkeypatch.setattr(s, "google_sheet_id", "", raising=False)
    monkeypatch.setattr(s, "google_service_account_json", "", raising=False)

    status, _, hint = asyncio.run(selftest.check_sheets())
    assert status == FAIL
    assert "GOOGLE_SERVICE_ACCOUNT_JSON" in hint or "GOOGLE_SHEET_ID" in hint


# ── the harness itself ─────────────────────────────────────────────────────


def test_timed_wrapper_converts_exceptions_into_failures():
    """A self-test that crashes tells you nothing. It must always report."""
    report = selftest.Report()

    async def explodes():
        raise RuntimeError("simulated outage")

    check = asyncio.run(selftest._timed(report, "deliberately broken", explodes))
    assert check.status == FAIL
    assert "RuntimeError" in check.detail
    assert "simulated outage" in check.detail
    assert check.ms is not None


def test_only_passing_checks_contribute_to_the_latency_baseline():
    """A failed step must not be reported as a real timing measurement."""
    report = selftest.Report()

    async def fails():
        return FAIL, "nope", ""

    async def works():
        return PASS, "fine", ""

    asyncio.run(selftest._timed(report, "broken step", fails))
    asyncio.run(selftest._timed(report, "good step", works))

    assert "broken step" not in report.timings
    assert "good step" in report.timings
    assert report.failed == 1


def test_report_counts_each_status_separately():
    report = selftest.Report()
    for status in (PASS, PASS, WARN, FAIL, SKIP):
        report.add(selftest.Check(f"check-{status}-{id(object())}", status))
    assert report.failed == 1
    assert len(report.checks) == 5


@pytest.mark.parametrize("flag", [True, False])
def test_full_run_never_raises_and_returns_an_exit_code(flag):
    """Whatever is broken in the environment, run() must return an int, not throw.

    With no reachable LLM/TTS in the test environment this exercises the
    failure paths end to end.
    """
    from voxflow_api.db import init_db

    init_db()
    code = asyncio.run(selftest.run(skip_audio=flag))
    assert code in (0, 1)
