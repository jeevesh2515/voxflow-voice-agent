# VoxFlow — Build Phases (Week-by-Week, Day-by-Day)

**Starting point:** Phases 0-2 already complete per `.planning/planning_overview.md`
(repo setup, DB foundation, staff auth + multi-tenant dashboard scaffolding).
This document picks up from here: fixing the latency-critical DB layer,
then real telephony, then hardening for a pilot.

Each day has **Theory** (what to understand first), **Checklist** (concrete
tasks), and **Definition of Done** (how you know it's actually finished).
Mark items `- [x]` as you complete them. Don't skip ahead — Week 2 assumes
Week 1's async DB fix is done and tested, not "probably fine."

---

## Week 1 — Fix the Foundation Before Adding Telephony

### Day 1 — Async database layer

**Theory:** `db.py` currently uses synchronous SQLAlchemy. Every DB call
inside `handle_turn` (an `async def`) blocks the event loop for its
duration. On a live phone call, this compounds across 2-3 tool calls per
turn into real, felt latency. This must be fixed before Twilio is wired in,
or you'll be debugging two hard problems (async correctness + real-time
audio) at once.

**Checklist:**
- [x] Add `asyncpg` (Postgres) + `aiosqlite` (SQLite) to `requirements.txt`
- [x] Convert `db.py` to `create_async_engine` + `async_sessionmaker`
- [x] Convert `session_scope()` to an `async def` context manager (`async_session_scope`)
- [x] Update every function in `tools.py` to `async def`, using
      `await db.execute(...)` / `await db.get(...)`
- [x] Update `execute_tool()` dispatcher in `tools.py` to `await` each tool
- [x] Update `runner.py`'s tool-calling loop to `await execute_tool(...)`
- [x] Run existing tests (`pytest apps/api/tests`), fix any breakage

**Definition of Done:** All existing tests pass. A manual check confirms
no `def` (non-async) function in `tools.py` makes a blocking DB call.

### Day 2 — Caching layer for hot reads

**Theory:** `check_stock` and `lookup_supplier` are called on nearly every
turn and change infrequently. A network round-trip to Postgres for each is
wasted latency. An in-process cache with a short TTL (30-60s) removes this
without adding infrastructure.

**Checklist:**
- [x] Add a simple TTL cache utility (a hand-rolled dict + timestamp) in a
      new `voxflow_api/cache.py`
- [x] Wrap `check_stock` reads with the cache, keyed by `(tenant_id, sku,
      warehouse)`
- [x] Wrap `lookup_supplier` reads with the cache, keyed by
      `(tenant_id, phone)`
- [x] Ensure `create_po` and any stock-mutating action invalidates the
      relevant cache entries
- [x] Add a note in ARCHITECTURE.md if you deviate from in-process caching
      (e.g. if you add Redis instead)

**Definition of Done:** Repeated calls to `check_stock` for the same SKU
within the TTL window don't hit the DB (verify via a log line or debugger,
not just "it feels faster").

### Day 3 — Supabase connection hygiene

**Theory:** Supabase provides both a direct connection string and a
pooled (pgbouncer, transaction-mode) connection string. A long-running
backend server (not a serverless function) should use the direct/session
connection, not the transaction-mode pooler, to avoid prepared-statement
and session-state issues.

**Checklist:**
- [ ] Confirm which connection string is currently in `.env` /
      `database_url`
- [ ] Switch to the direct (session mode) connection string for the
      FastAPI backend
- [ ] Confirm the Supabase project region matches (or is closest to)
      wherever the backend will actually be deployed
- [ ] Document the final connection string pattern in `.env.example`
      (with placeholder values, never real keys)

**Definition of Done:** Backend connects successfully using the direct
connection string, confirmed via `verify_db.py`.

### Day 4 — Latency measurement baseline

**Theory:** You can't know if Week 1's fixes helped without a number to
compare against. Measure now, before Twilio adds real audio latency on
top.

**Checklist:**
- [ ] Add timing logs around: STT, each LLM iteration, each DB call, TTS
      (some of this exists already in `runner.py`'s `llm.turn` log — extend
      it to cover DB and TTS)
- [ ] Run 5 test conversations through the browser simulator, record
      per-step timings
- [ ] Write the baseline numbers into `MEMORY.md` under a "Latency
      Baseline" note

**Definition of Done:** You have real numbers (not guesses) for STT/LLM/DB/
TTS latency per turn, recorded somewhere you'll reference again after
Twilio integration.

### Day 5 — Buffer day / catch-up

**Theory:** Week 1 touches core infra; things break in ways you don't
expect. This day exists on purpose.

**Checklist:**
- [ ] Fix anything from Days 1-4 that isn't actually done
- [ ] Re-run the full test suite
- [ ] Update MEMORY.md with true current status before moving to Week 2

**Definition of Done:** Everything checked `[x]` above is genuinely true,
not aspirational.

---

## Week 2 — Real Telephony (Twilio)

### Day 6 — Twilio account + webhook skeleton

**Theory:** See ARCHITECTURE.md section 6 for the integration plan.
Start with the simplest possible thing that proves the audio path works
before wiring in STT/agent/TTS.

**Checklist:**
- [ ] Set up Twilio account, buy/configure a trial number
- [ ] Add a new FastAPI route for the Twilio Voice webhook
      (`POST /twilio/voice`), returning TwiML that plays a static test
      message
- [ ] Confirm calling the Twilio number plays the test message

**Definition of Done:** Calling the Twilio number produces audible audio
from your server — proves the basic webhook + TwiML path works.

### Day 7 — Media Streams WebSocket

**Theory:** Twilio Media Streams opens a WebSocket and sends base64-encoded
mulaw 8kHz audio frames. This is a different format than the pipeline
currently expects (16kHz PCM from the browser simulator) — a resampling/
transcoding step is needed.

**Checklist:**
- [ ] Update TwiML to open a `<Connect><Stream>` to a new WebSocket route
- [ ] Implement the WebSocket handler receiving Twilio's audio frames
- [ ] Add mulaw→PCM decoding and 8kHz→16kHz resampling (e.g. via
      `audioop`/`av`, already a dependency)
- [ ] Log received audio frame count/size to confirm data is flowing

**Definition of Done:** Speaking on a real call produces logged audio
frames on the server, correctly decoded (verify by writing a short sample
to a `.wav` file and listening to it).

### Day 8 — Wire STT into the Twilio stream

**Checklist:**
- [ ] Feed decoded/resampled PCM into the existing `SpeechToText`
      pipeline
- [ ] Implement end-of-utterance detection appropriate for phone audio
      (may need a different silence threshold than the browser simulator)
- [ ] Log transcripts from real phone calls

**Definition of Done:** Speaking a test sentence on a real call produces
an accurate transcript in the logs.

### Day 9 — Wire agent + TTS into the Twilio stream, full loop

**Checklist:**
- [ ] Connect transcript → `AgentRunner.handle_turn` → TTS → encode back
      to mulaw 8kHz → stream to Twilio
- [ ] Run one complete real phone call: greet → identify → stock check →
      confirm

**Definition of Done:** A real phone call to the Twilio number completes
one full scenario correctly, entirely by voice.

### Day 10 — Multi-caller real-world testing

**Checklist:**
- [ ] Test with at least 3 different real people calling in, different
      accents/phone qualities
- [ ] Log every failure mode observed (misheard words, awkward timing,
      dropped calls)
- [ ] Fix only the highest-frequency failure — resist fixing everything
      today
- [ ] Update MEMORY.md with real latency numbers now that Twilio is in
      the loop, compared against the Week 1 baseline

**Definition of Done:** 3+ real people have completed a real call
successfully; failure modes are documented, not just noticed.

---

## Week 3 — Auth Hardening & Live Dashboard

### Day 11 — Real Supabase Auth for staff

**Theory:** Current staff auth is `localStorage`-based per
`security_audit.md` — fine for a demo, not for a real pilot with a real
company's data.

**Checklist:**
- [ ] Wire `apps/web/src/app/sign-in` and `sign-up` to real Supabase Auth
      (email/password or magic link)
- [ ] Replace `localStorage` session handling with Supabase session
      management
- [ ] Update `TenantProvider` to derive active tenant from the
      authenticated user's actual tenant membership, not client-side state
      alone

**Definition of Done:** A staff user cannot access the dashboard without a
real Supabase-authenticated session; tenant scoping is derived from the
authenticated identity, not just local storage.

### Day 12 — RLS enforcement, verified

**Checklist:**
- [ ] Enable RLS on all tables per `schema.md` in the actual Supabase
      project (if not already applied)
- [ ] Create a second real test tenant with its own seed data
- [ ] Deliberately attempt a cross-tenant query and confirm it's blocked
      at the database level, not just the application level

**Definition of Done:** A cross-tenant data access attempt fails at the
RLS layer even if application code were buggy — tested, not assumed.

### Day 13 — Caller PIN auth (Tier 2)

**Theory:** Current caller verification (city/GSTIN) is reasonable for
read actions (stock check) but weak for write actions (placing a PO).

**Checklist:**
- [ ] Add a PIN field to the `suppliers` table (or use last-PO reference
      as an alternative — pick one, document in RULES.md)
- [ ] Gate `create_po` behind successful Tier 2 verification
- [ ] Test: a caller who fails Tier 2 auth cannot place an order, and the
      attempt is logged, not silently dropped

**Definition of Done:** A test call attempting `create_po` without valid
Tier 2 auth is blocked and logged as an auth failure.

### Day 14 — Supabase Realtime on the dashboard

**Checklist:**
- [ ] Wire the `/dashboard/calls` page to Supabase Realtime subscriptions
      on the `calls` table
- [ ] Confirm a new call log appears on the dashboard live, without a
      manual refresh

**Definition of Done:** Making a real test call causes its log entry to
appear on the dashboard within a couple seconds, no refresh needed.

### Day 15 — Buffer day / catch-up

**Checklist:**
- [ ] Fix anything incomplete from Days 11-14
- [ ] Update MEMORY.md

---

## Week 4 — Escalation UX, Security Pass, Pilot Prep

### Day 16 — In-progress call status

**Checklist:**
- [ ] Add live status updates during an active call (current intent,
      entities captured so far) visible on the dashboard, not just after
      the call ends
- [ ] Test with a real in-progress call

**Definition of Done:** An active call shows live status on the dashboard
while still in progress.

### Day 17 — Escalation queue

**Checklist:**
- [ ] Add a distinct "escalated calls" view on the dashboard
- [ ] Add a resolution field staff can fill in once followed up
- [ ] Test end-to-end: trigger an escalation, confirm it's flagged,
      resolve it, confirm the resolution persists

**Definition of Done:** An escalated call is visually distinct and can be
marked resolved by a staff user.

### Day 18 — Security pass

**Checklist:**
- [ ] Re-run through `security_audit.md` and confirm every mitigation
      listed is actually true in the current code, not aspirational
- [ ] Check for any hardcoded secrets, test API keys, or debug endpoints
      that shouldn't ship
- [ ] Rate-limit the Twilio webhook and WebSocket endpoints

**Definition of Done:** `security_audit.md` is updated to reflect actual
current state, with any gaps explicitly noted, not silently assumed fixed.

### Day 19 — The real conversation

**Theory:** This is the step that's been deferred since Day 1 of the
project. By now you have something real to show, which makes the
conversation far more productive than it would have been at the start.

**Checklist:**
- [ ] Talk to the friend at Varun Beverages (or equivalent contact) —
      show a real demo call, ask about actual workflow gaps
- [ ] Update PRD.md section 5 (Assumed Workflow) based on what you learn
- [ ] Identify the single highest-value fix based on this conversation

**Definition of Done:** PRD.md no longer says "assumed" for the core
workflow — it reflects a real conversation.

### Day 20 — Pilot-readiness fixes

**Checklist:**
- [ ] Implement whatever the Day 19 conversation surfaced as
      highest-priority
- [ ] Final read-through of MEMORY.md, PHASES.md, PRD.md — make sure they
      reflect reality, not the plan as originally imagined

**Definition of Done:** You could hand this repo + a live demo to the
Varun Beverages contact today and it would hold up.
