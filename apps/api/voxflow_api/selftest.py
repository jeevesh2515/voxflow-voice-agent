"""End-to-end self-test — proves the deployment works before Twilio is involved.

    docker compose -f deploy/docker-compose.prod.yml exec api python -m voxflow_api.selftest

Why this exists
---------------
Until now the only way to find out whether a deployment worked was to ring the
number and listen to silence. That gives you one bit of information ("it didn't
work") and no idea which of six services is at fault.

This exercises every component of a real call **except Twilio's transport**, in
the same order a call uses them, and times each one. If a live call then fails,
you know the problem is the telephony layer specifically — not the LLM, not the
database, not the audio codecs.

It also produces the per-turn latency baseline that PHASES.md Week 1 Day 4 asks
for and that has never been measured.

Safety
------
Read-only against your business data. The agent turn runs against whatever is
already seeded and writes nothing. The only optional write is a single clearly
marked test row if Google Sheets is enabled. Safe to run against production.

Exit code 0 = every non-skipped check passed.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine


# ── tiny result model ───────────────────────────────────────────────────────

PASS, FAIL, SKIP, WARN = "PASS", "FAIL", "SKIP", "WARN"

_COLOUR = {
    PASS: "\033[32m",
    FAIL: "\033[31m",
    SKIP: "\033[90m",
    WARN: "\033[33m",
}
_RESET = "\033[0m"
# --debug prints full tracebacks. "gaierror: Name or service not known" with no
# stack tells you nothing about WHICH resolution call failed or why.
_DEBUG = False
_USE_COLOUR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _paint(status: str) -> str:
    if not _USE_COLOUR:
        return status
    return f"{_COLOUR.get(status, '')}{status}{_RESET}"


@dataclass
class Check:
    name: str
    status: str
    ms: int | None = None
    detail: str = ""
    hint: str = ""


@dataclass
class Report:
    checks: list[Check] = field(default_factory=list)
    timings: dict[str, int] = field(default_factory=dict)

    def add(self, c: Check) -> Check:
        self.checks.append(c)
        icon = {PASS: "✅", FAIL: "❌", SKIP: "⏭️ ", WARN: "⚠️ "}[c.status]
        ms = f"{c.ms:>6}ms" if c.ms is not None else "        "
        print(f"  {icon} {_paint(c.status):<4} {ms}  {c.name}")
        if c.detail:
            for line in c.detail.splitlines():
                print(f"                       {line}")
        if c.status in (FAIL, WARN) and c.hint:
            for line in c.hint.splitlines():
                print(f"                       → {line}")
        return c

    @property
    def failed(self) -> int:
        return sum(1 for c in self.checks if c.status == FAIL)


async def _timed(
    report: Report, name: str, fn: Callable[[], Coroutine[Any, Any, tuple[str, str, str]]]
) -> Check:
    """Run one check, time it, never let an exception escape."""
    t0 = time.perf_counter()
    try:
        status, detail, hint = await fn()
    except Exception as e:  # noqa: BLE001 — a self-test must report, not crash
        status, detail, hint = FAIL, f"{type(e).__name__}: {e}", ""
        if _DEBUG:
            import traceback

            detail += "\n" + "".join(traceback.format_exc()).rstrip()
    ms = int((time.perf_counter() - t0) * 1000)
    c = report.add(Check(name, status, ms, detail, hint))
    if status == PASS:
        report.timings[name] = ms
    return c


# ── 1. configuration ───────────────────────────────────────────────────────


async def check_config() -> tuple[str, str, str]:
    from .config import get_settings

    s = get_settings()
    lines = [
        f"LLM        {s.llm_provider} / {s.groq_model if s.llm_provider == 'groq' else '-'}",
        f"STT        {s.stt_provider} / {s.groq_stt_model if s.stt_provider == 'groq' else s.whisper_model_size}",
        f"TTS        edge-tts ({s.tts_voice_hi} / {s.tts_voice_en})",
        f"DB         {'postgres' if 'postgres' in s.database_url else 'sqlite' if s.database_url else 'UNSET'}",
        f"Sheets     {'enabled' if s.sheets_enabled else 'disabled'}",
        f"Public URL {s.public_base_url or 'UNSET'}",
        f"Signature  {'validated' if s.twilio_validate_signature else 'NOT validated'}",
    ]
    problems = []
    if not s.database_url:
        problems.append("DATABASE_URL is empty")
    if s.stt_provider == "groq" and not s.groq_api_key:
        problems.append("STT_PROVIDER=groq but GROQ_API_KEY is empty")
    if s.llm_provider == "groq" and not s.groq_api_key:
        problems.append("LLM_PROVIDER=groq but GROQ_API_KEY is empty")

    detail = "\n".join(lines)
    if problems:
        return FAIL, detail + "\n" + "; ".join(problems), "Fix .env, then: docker compose ... up -d"
    return PASS, detail, ""


# ── 2. database + migrations ───────────────────────────────────────────────

_EXPECTED_TABLES = [
    "tenants", "suppliers", "products", "stock", "orders", "shipments",
    "calls", "appointments", "worksheet_logs", "communication_logs",
    "tenant_phone_numbers",
]
# Columns added by migrations/001 — their absence means the migration wasn't run.
_MIGRATION_COLUMNS = {
    "orders": ["customer_po_ref", "po_signed", "po_signed_at", "dispatched_at"],
    "calls": ["reason", "solution", "resolution_status", "satisfaction", "verified"],
    "suppliers": ["contact_type"],
}


def _db_target() -> str:
    """Host:port the engine will actually dial, with the password masked.

    Without this a DNS or routing failure just says "Name or service not known"
    and you cannot tell whether the container even has the URL you think it has.
    That ambiguity cost real debugging time.
    """
    try:
        from .db import _async_engine

        u = _async_engine.url
        return f"{u.username}@{u.host}:{u.port}/{u.database}"
    except Exception:  # noqa: BLE001
        return "<could not read engine URL>"


async def check_database() -> tuple[str, str, str]:
    from sqlalchemy import inspect, text

    from .db import _async_engine

    async with _async_engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
        tables = await conn.run_sync(lambda c: set(inspect(c).get_table_names()))
        cols: dict[str, set[str]] = {}
        for t in _MIGRATION_COLUMNS:
            if t in tables:
                cols[t] = await conn.run_sync(
                    lambda c, t=t: {col["name"] for col in inspect(c).get_columns(t)}
                )

    missing_tables = [t for t in _EXPECTED_TABLES if t not in tables]
    if missing_tables:
        return (
            FAIL,
            f"{len(tables)} tables present; missing: {', '.join(missing_tables)}",
            "The database is empty. In the Supabase dashboard → SQL Editor → New query,\n"
            "paste migrations/000_base_schema.sql and Run. That one file creates every\n"
            "table, index and RLS policy, and is generated from the ORM models so it\n"
            "cannot disagree with the code. Then seed: docker compose ... exec api\n"
            "python -m voxflow_api.seed",
        )

    missing_cols = [
        f"{t}.{c}" for t, expected in _MIGRATION_COLUMNS.items()
        for c in expected if c not in cols.get(t, set())
    ]
    if missing_cols:
        return (
            FAIL,
            f"all {len(_EXPECTED_TABLES)} tables exist but migration columns are missing: "
            + ", ".join(missing_cols),
            "You ran schema.md but not the migration.\n"
            "Run migrations/001_customer_support_flow.sql in the Supabase SQL Editor.",
        )

    return PASS, f"all {len(_EXPECTED_TABLES)} tables + migration 001 columns present", ""


async def probe_database_layers() -> None:
    """Isolate a database failure to a specific layer.

    `gaierror` from SQLAlchemy could originate in the dialect, in asyncpg, or in
    asyncio's resolver — and they fail for different reasons. Testing each
    separately turns one ambiguous error into a definite answer.
    """
    import socket
    import traceback

    from .db import _async_engine

    u = _async_engine.url
    print()
    print("  Database probe (--debug)")
    print("  " + "─" * 68)
    print(f"    host={u.host!r}  port={u.port!r}  user={u.username!r}  db={u.database!r}")
    print(f"    driver={u.drivername!r}")

    # Layer 1 — blocking IPv4-only lookup (what the earlier manual test did).
    try:
        print(f"    [1] socket.gethostbyname   -> {socket.gethostbyname(u.host)}")
    except Exception as e:  # noqa: BLE001
        print(f"    [1] socket.gethostbyname   -> FAILED {type(e).__name__}: {e}")

    # Layer 2 — getaddrinfo, which is what asyncio and asyncpg actually use.
    # Unlike gethostbyname this requests A *and* AAAA, so it can fail on hosts
    # with broken IPv6 even when the IPv4-only lookup succeeds.
    for family, label in ((socket.AF_UNSPEC, "AF_UNSPEC (A+AAAA)"), (socket.AF_INET, "AF_INET (A only)")):
        try:
            res = socket.getaddrinfo(u.host, u.port, family, socket.SOCK_STREAM)
            print(f"    [2] getaddrinfo {label:<20} -> {[r[4] for r in res]}")
        except Exception as e:  # noqa: BLE001
            print(f"    [2] getaddrinfo {label:<20} -> FAILED {type(e).__name__}: {e}")

    # Layer 3 — asyncio's resolver on the running loop.
    try:
        loop = asyncio.get_running_loop()
        res = await loop.getaddrinfo(u.host, u.port, type=socket.SOCK_STREAM)
        print(f"    [3] loop.getaddrinfo       -> {[r[4] for r in res]}")
    except Exception as e:  # noqa: BLE001
        print(f"    [3] loop.getaddrinfo       -> FAILED {type(e).__name__}: {e}")

    # Layer 4 — raw asyncpg, bypassing SQLAlchemy entirely.
    try:
        import asyncpg

        conn = await asyncpg.connect(
            host=u.host, port=u.port, user=u.username,
            password=u.password, database=u.database, timeout=15,
        )
        print(f"    [4] raw asyncpg.connect    -> OK, SELECT 1 = {await conn.fetchval('SELECT 1')}")
        await conn.close()
    except Exception as e:  # noqa: BLE001
        print(f"    [4] raw asyncpg.connect    -> FAILED {type(e).__name__}: {e}")
        traceback.print_exc()
    print("  " + "─" * 68)


async def check_seed_data() -> tuple[str, str, str]:
    """Not a failure if empty — but you cannot demo without data."""
    from sqlalchemy import func, select

    from .db import Order, Supplier, Tenant, TenantPhoneNumber, async_session_scope

    async with async_session_scope() as db:
        counts = {}
        for label, model in (
            ("tenants", Tenant), ("contacts", Supplier),
            ("orders", Order), ("phone numbers", TenantPhoneNumber),
        ):
            counts[label] = (await db.execute(select(func.count()).select_from(model))).scalar() or 0

    detail = "  ".join(f"{k}={v}" for k, v in counts.items())
    if counts["tenants"] == 0 or counts["contacts"] == 0:
        return WARN, detail, "Seed demo data:  python -m voxflow_api.seed --reset"
    if counts["phone numbers"] == 0:
        return (
            WARN, detail,
            "No tenant_phone_numbers rows — inbound calls will fall back to\n"
            "DEFAULT_TENANT_ID. Map your Twilio number before going multi-tenant.",
        )
    return PASS, detail, ""


# ── 3. LLM ─────────────────────────────────────────────────────────────────


async def check_llm() -> tuple[str, str, str]:
    from .llm.base import ChatTurn
    from .llm.factory import get_llm

    llm = get_llm()
    resp = await llm.chat(
        messages=[ChatTurn(role="user", content="Reply with exactly the word: ready")],
        tools=None,
    )
    text = (resp.content or "").strip()
    if not text:
        return FAIL, "empty response", "Check GROQ_API_KEY and your Groq rate limit."
    return PASS, f"{llm.name}/{llm.model} → {text[:40]!r}", ""


# ── 4. TTS → 5. STT round-trip (the whole audio path, minus Twilio) ────────

_PHRASE = "Please check my purchase order number one two three."


async def check_tts(state: dict[str, Any]) -> tuple[str, str, str]:
    from .voice.tts import TextToSpeech

    result = await TextToSpeech().synth(_PHRASE, lang_hint="en")
    if not result.audio_bytes:
        return FAIL, "edge-tts returned no audio", "Check outbound HTTPS to Microsoft's edge service."
    state["mp3"] = result.audio_bytes
    return PASS, f"{len(result.audio_bytes):,} bytes of {result.mime}", ""


async def check_codecs(state: dict[str, Any]) -> tuple[str, str, str]:
    """Decode the TTS MP3 the same way the Twilio path does, then round-trip it."""
    from .routes.twilio import mp3_to_pcm8k, mulaw_to_pcm, pcm_to_mulaw, resample_8k_to_16k

    mp3 = state.get("mp3")
    if not mp3:
        return SKIP, "no TTS audio to decode", ""

    pcm8k = mp3_to_pcm8k(mp3)
    if not pcm8k:
        return FAIL, "MP3 decoded to zero PCM bytes", "PyAV may be missing its bundled codecs."

    mulaw = pcm_to_mulaw(pcm8k)          # what we send to a caller
    back = mulaw_to_pcm(mulaw)           # what a caller's audio looks like inbound
    pcm16k = resample_8k_to_16k(back)    # what STT receives

    if len(mulaw) != len(pcm8k) // 2:
        return FAIL, "mulaw length mismatch", ""
    if len(pcm16k) != len(back) * 2:
        return FAIL, "resampler did not double the sample count", ""

    state["pcm16k"] = pcm16k
    secs = len(pcm16k) / 2 / 16000
    return PASS, f"{secs:.2f}s audio · mp3→pcm8k→mulaw→pcm→16k all consistent", ""


async def check_stt(state: dict[str, Any]) -> tuple[str, str, str]:
    """Feed our own synthesised speech back through STT.

    This is the strongest signal in the whole self-test: if a known phrase
    survives TTS → mulaw → STT and comes back recognisable, the entire audio
    pipeline is sound and only Twilio's transport is unverified.
    """
    import numpy as np

    from .voice.stt import SpeechToText

    pcm16k = state.get("pcm16k")
    if not pcm16k:
        return SKIP, "no decoded audio available", ""

    samples = np.frombuffer(pcm16k, dtype="<i2").astype(np.float32) / 32768.0
    loop = asyncio.get_running_loop()
    stt = SpeechToText.instance()
    tr = await loop.run_in_executor(
        None, lambda: stt.transcribe_pcm(samples, sample_rate=16000, language="en")
    )

    heard = (tr.text or "").lower()
    if not heard:
        return (
            FAIL, "transcript was empty",
            "STT could not hear our own synthesised speech. Check GROQ_API_KEY,\n"
            "the Groq rate limit, and outbound HTTPS to api.groq.com.",
        )

    # Don't demand an exact match — Whisper punctuates and spells numbers freely.
    expected = {"check", "purchase", "order"}
    hits = {w for w in expected if w in heard}
    detail = f"{stt.provider_name} heard: {tr.text.strip()[:70]!r} (conf {tr.confidence:.2f})"
    if len(hits) < 2:
        return (
            WARN, detail,
            f"Only matched {sorted(hits)} of {sorted(expected)}. Audio path works but\n"
            "accuracy looks low — check the STT model setting.",
        )
    return PASS, detail, ""


# ── 6. the agent itself ────────────────────────────────────────────────────


async def check_agent_turn() -> tuple[str, str, str]:
    """Run one real conversational turn through the tool-calling loop."""
    from sqlalchemy import select

    from .agent.runner import AgentRunner
    from .config import get_settings
    from .db import Supplier, async_session_scope
    from .voice.pipeline import CallSession

    tenant = get_settings().default_tenant_id
    async with async_session_scope() as db:
        sup = (
            await db.execute(select(Supplier).where(Supplier.tenant_id == tenant).limit(1))
        ).scalars().first()
        if not sup:
            return (
                SKIP, f"no contacts seeded for tenant {tenant!r}",
                "python -m voxflow_api.seed --reset",
            )
        phone, company, city = sup.phone, sup.name, sup.city

    # The caller states their company AND their city AND asks a concrete
    # question — everything `verify_caller` and `check_po_status` need. A
    # correct agent cannot answer this from its own knowledge, so a turn with
    # no tool call means it is improvising.
    utterance = f"Hello, this is {company} calling from {city}. Has our PO been signed?"

    attempts: list[tuple[str, list[str]]] = []
    for _ in range(2):  # LLMs are stochastic; one miss is not a verdict
        session = CallSession(call_id=f"selftest-{int(time.time())}", tenant_id=tenant)
        session.caller_phone = phone
        result = await AgentRunner().handle_turn(session=session, user_text=utterance)
        tools_used = [a.get("name") for a in result.actions]
        attempts.append(((result.reply or "").strip(), tools_used))
        if tools_used:
            break

    reply, tools_used = attempts[-1]
    if not reply and not tools_used:
        return FAIL, f"agent produced no reply over {len(attempts)} attempts", ""

    detail = f"reply: {reply[:80]!r}\ntools: {tools_used or 'none'}"
    if len(attempts) > 1:
        detail += f"  (tool call on attempt {len(attempts)} of 2)"

    if not tools_used:
        # This is a failure, not a warning. An agent that answers questions
        # about orders without reading the database will state invented
        # quantities and dispatch dates to a paying customer, in a confident
        # voice, with no error anywhere. It is the worst outcome this system
        # can produce — worse than the call failing outright.
        return (
            FAIL,
            detail + "\n  (both attempts answered without touching the database)"
            + "".join(f"\n   attempt {i + 1}: {r[:60]!r}" for i, (r, _) in enumerate(attempts)),
            "The agent replied to a direct order question without calling a tool.\n"
            "On a real call it would invent the answer. Check agent/prompts.py — the\n"
            "'Tools are not optional' section — and confirm TOOL_DEFINITIONS reaches\n"
            "the provider (runner.py passes tools=TOOL_DEFINITIONS to llm.chat).",
        )
    return PASS, detail, ""


# ── 7. Google Sheets (optional) ────────────────────────────────────────────


async def check_sheets() -> tuple[str, str, str]:
    from .config import get_settings
    from .integrations.gsheets import get_sheets_client

    s = get_settings()
    if not s.sheets_enabled:
        return SKIP, "SHEETS_ENABLED=false (supported — outcomes still go to Postgres)", ""

    client = get_sheets_client()
    if not client.is_configured():
        return (
            FAIL, "SHEETS_ENABLED=true but the client is not configured",
            "GOOGLE_SERVICE_ACCOUNT_JSON / GOOGLE_SHEET_ID missing or malformed.",
        )

    res = await client.append_call_outcome({
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "call_id": "SELFTEST — safe to delete",
        "caller_phone": "-", "caller_name": "-", "company": "VoxFlow self-test",
        "verified": False, "language": "en",
        "reason": "Automated self-test", "solution": "No action required",
        "resolution_status": "resolved", "satisfaction": "neutral",
        "follow_up_required": False, "escalated": False,
        "duration_sec": 0, "related_order": "-",
    })
    if not res.get("ok"):
        # Google's status code says exactly what is wrong. The previous hint
        # blamed sharing for every failure, which sent debugging in the wrong
        # direction for a 400 (a malformed range — a bug on our side).
        reason = str(res.get("reason", ""))
        detail = str(res.get("detail", ""))
        if reason == "http_403" or "PERMISSION_DENIED" in detail:
            hint = (
                "403 = the service account cannot open this spreadsheet.\n"
                "Open the sheet → Share → paste the client_email from your service-account\n"
                "JSON → Editor. Sharing failures are silent until you look here."
            )
        elif reason == "http_404":
            hint = "404 = GOOGLE_SHEET_ID is wrong. It is the long id in the sheet's URL,\nbetween /d/ and /edit."
        elif reason == "http_400":
            hint = (
                "400 = the range was rejected, which is our bug, not your configuration.\n"
                "Tab names with spaces must be quoted in A1 notation. Check GOOGLE_SHEET_TAB\n"
                "and confirm the image is current (compare the fingerprint above)."
            )
        elif reason == "auth_failed":
            hint = (
                "The service-account JSON did not mint a token. Check GOOGLE_CREDENTIALS_JSON\n"
                "is valid JSON and that the Sheets API is enabled on that Google Cloud project."
            )
        else:
            hint = "Check GOOGLE_SHEET_ID, GOOGLE_SHEET_TAB and that the sheet is shared as Editor."
        return FAIL, f"append failed: {reason} {detail}", hint
    return PASS, f"test row appended to {res.get('updated_range') or s.google_sheet_tab}", ""


# ── runner ─────────────────────────────────────────────────────────────────


async def run(skip_audio: bool = False) -> int:
    from .config import get_settings

    print()
    print("VoxFlow self-test")
    print("═" * 72)
    print("Exercises every part of a real call except Twilio's transport.")
    print()

    from ._fingerprint import code_fingerprint

    report = Report()
    # If this does not match what preflight.sh printed, the image is stale and
    # every result below describes code you are no longer looking at.
    print(f"  code fingerprint {code_fingerprint()}  "
          "(must match scripts/preflight.sh — if not, rebuild with --build)")
    state: dict[str, Any] = {}

    print("Configuration")
    await _timed(report, "settings load + provider wiring", check_config)

    print()
    print("Data layer")
    print(f"  (connecting to {_db_target()})")
    db_ok = await _timed(report, "database connect + schema + migration 001", check_database)
    if db_ok.status == FAIL and _DEBUG:
        await probe_database_layers()
    if db_ok.status == FAIL and "gaierror" in db_ok.detail:
        print("                       → DNS lookup failed INSIDE the container.")
        print("                         The host resolving it is not enough — check the")
        print("                         container's own view:")
        print("                           docker compose ... exec -T api python -c \\")
        print("                             \"import os;print(os.environ.get('DATABASE_URL'))\"")
        print("                         If it differs from .env, the container was restarted")
        print("                         but not RECREATED. Fix: add --force-recreate")
    if db_ok.status == PASS:
        await _timed(report, "demo data present", check_seed_data)

    print()
    print("AI services")
    await _timed(report, "LLM completion (Groq)", check_llm)

    if skip_audio:
        report.add(Check("audio pipeline", SKIP, None, "--skip-audio given"))
    else:
        await _timed(report, "TTS synthesis (edge-tts)", lambda: check_tts(state))
        await _timed(report, "audio codecs (mp3→mulaw→pcm→16k)", lambda: check_codecs(state))
        await _timed(report, "STT round-trip (Groq Whisper)", lambda: check_stt(state))

    print()
    print("Agent")
    if db_ok.status == PASS:
        await _timed(report, "full conversational turn + tool calls", check_agent_turn)
    else:
        report.add(Check("full conversational turn", SKIP, None, "database unavailable"))

    print()
    print("Integrations")
    await _timed(report, "Google Sheets append", check_sheets)

    # ── latency baseline ──────────────────────────────────────────────────
    stt_ms = report.timings.get("STT round-trip (Groq Whisper)")
    llm_ms = report.timings.get("LLM completion (Groq)")
    tts_ms = report.timings.get("TTS synthesis (edge-tts)")
    agent_ms = report.timings.get("full conversational turn + tool calls")

    print()
    print("Latency baseline  (PHASES.md Week 1 Day 4)")
    print("─" * 72)
    for label, val in (
        ("speech-to-text", stt_ms), ("LLM single turn", llm_ms),
        ("text-to-speech", tts_ms), ("agent turn incl. tools + DB", agent_ms),
    ):
        print(f"  {label:<28} {val if val is not None else '—':>6}{'ms' if val else ''}")
    if all(v is not None for v in (stt_ms, agent_ms, tts_ms)):
        total = stt_ms + agent_ms + tts_ms
        print(f"  {'─' * 34}")
        print(f"  {'ESTIMATED PER-TURN SILENCE':<28} {total:>6}ms")
        verdict = (
            "excellent — feels conversational" if total < 1500
            else "acceptable" if total < 2500
            else "SLOW — callers will think the line dropped"
        )
        print(f"  {'':<28} {verdict}")
        print()
        print("  Record these in MEMORY.md under 'Latency Baseline'.")

    # ── summary ───────────────────────────────────────────────────────────
    counts = {s: sum(1 for c in report.checks if c.status == s) for s in (PASS, WARN, FAIL, SKIP)}
    print()
    print("═" * 72)
    print(
        f"  {counts[PASS]} passed · {counts[WARN]} warnings · "
        f"{counts[FAIL]} failed · {counts[SKIP]} skipped"
    )
    print()
    if report.failed:
        print("  ❌ Fix the failures above before wiring up Twilio.")
        print()
        return 1

    s = get_settings()
    print("  ✅ Every component works. The only unverified layer is Twilio itself.")
    print()
    print("  Next:")
    print("    1. Point your Twilio number's voice webhook at")
    print(f"       {s.public_base_url or 'https://YOUR-DOMAIN'}/twilio/voice   (HTTP POST)")
    print("    2. Map the number:  INSERT INTO tenant_phone_numbers ...")
    print("    3. Call it.")
    print()
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="VoxFlow end-to-end self-test")
    ap.add_argument(
        "--skip-audio", action="store_true",
        help="skip TTS/STT/codec checks (faster; avoids Groq STT quota)",
    )
    ap.add_argument(
        "--debug", action="store_true",
        help="print full tracebacks and probe the database connection layer by layer",
    )
    args = ap.parse_args()

    global _DEBUG
    _DEBUG = args.debug

    from .logging import setup_logging

    # Keep structured logs out of the report; the report IS the output.
    setup_logging()
    import logging

    logging.getLogger().setLevel(logging.WARNING)

    sys.exit(asyncio.run(run(skip_audio=args.skip_audio)))


if __name__ == "__main__":
    main()
