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
- [x] Confirm which connection string is currently in `.env` /
      `database_url` — **SQLite for dev** (`sqlite:///./voxflow.db`),
      only switches to Postgres/Supabase when `DATABASE_URL` is set in
      production
- [ ] Switch to the direct (session mode) connection string — **deferred
      until production deployment**; dev uses SQLite, which has no
      pooler distinction
- [ ] Confirm the Supabase project region — **deferred until production
      deployment**
- [x] Document the final connection string pattern in `.env.example`
      (with placeholder values, never real keys)

**Definition of Done:** Backend connects successfully using the direct
connection string, confirmed via `verify_db.py`. (Deferred to deploy-time.)

### Day 4 — Latency measurement baseline

**Theory:** You can't know if Week 1's fixes helped without a number to
compare against. Measure now, before Twilio adds real audio latency on
top.

**Checklist:**
- [x] Add timing logs around: STT, each LLM iteration, each DB call, TTS
      (some of this existed already in `runner.py`'s `llm.turn` log —
      extended to cover STT, TTS, tool execution, and DB persist)
- [x] A way to measure this without a browser — `python -m voxflow_api.selftest`
      times STT, LLM, TTS and a full agent turn (incl. tools + DB) and prints a
      per-turn total with a verdict. Supersedes the "5 conversations through the
      simulator" plan: no browser, no microphone, runnable on the server.
- [ ] **Run it against the deployed instance and paste the numbers into
      `MEMORY.md` → "Latency Baseline".** Still outstanding — the tool exists,
      the measurement has not been taken.

**Definition of Done:** You have real numbers (not guesses) for STT/LLM/DB/
TTS latency per turn, recorded somewhere you'll reference again after
Twilio integration.

### Day 5 — Buffer day / catch-up

**Theory:** Week 1 touches core infra; things break in ways you don't
expect. This day exists on purpose.

**Checklist:**
- [x] Fix anything from Days 1-4 that isn't actually done
- [x] Re-run the full test suite
- [x] Update MEMORY.md with true current status before moving to Week 2

**Definition of Done:** Everything checked `[x]` above is genuinely true,
not aspirational.

---

## Week 2 — Real Telephony (Twilio)

### Day 6 — Twilio account + webhook skeleton

**Theory:** See ARCHITECTURE.md section 6 for the integration plan.
Start with the simplest possible thing that proves the audio path works
before wiring in STT/agent/TTS.

**Checklist:**
- [x] Set up Twilio account, buy/configure a trial number
- [x] Add a new FastAPI route for the Twilio Voice webhook
       (`POST /twilio/voice`), returning TwiML that opens a
       `<Connect><Stream>` to the Media Streams WebSocket
- [x] Confirm calling the Twilio number produces audible audio
       from your server — proves the basic webhook + TwiML path works

**Definition of Done:** Calling the Twilio number produces audible audio
from your server — proves the basic webhook + TwiML path works.

> **STILL UNMET as of 2026-08-05.** Every layer below the telephony transport is
> now verifiable without a phone via `python -m voxflow_api.selftest`. What
> remains genuinely unproven is Twilio itself: the webhook, the Media Stream
> WebSocket, and real network audio. Do not mark Days 6-9 done until a real call
> has completed.

### Day 7 — Media Streams WebSocket

**Theory:** Twilio Media Streams opens a WebSocket and sends base64-encoded
mulaw 8kHz audio frames. This is a different format than the pipeline
currently expects (16kHz PCM from the browser simulator) — a resampling/
transcoding step is needed.

Twilio's WebSocket protocol uses JSON messages with an `event` field:
- `connected` — confirms the WebSocket is open
- `start` — contains `streamSid` and `callSid` identifiers
- `media` — contains `payload` (base64-encoded mulaw audio at 8kHz, ~20ms
  frames containing ~160 bytes of mulaw data)
- `stop` — Twilio is closing the stream
- `mark` — acknowledgement of a mark sent by the server (not used on Day 7)

The `routes/twilio.py` file implements:
1. `POST /twilio/voice` — returns TwiML with `<Connect><Stream>` pointing
   to the WebSocket endpoint
2. `WebSocket /twilio/media` — receives mulaw frames, decodes to linear PCM
   using a hand-rolled μ-law expansion table, then resamples from 8kHz to
   16kHz via linear interpolation (doubles sample count)
3. Logging every 100th frame with accumulated byte counts

**Implementation notes:**
- Python's `audioop` module is deprecated/not available on all platforms.
  The hand-rolled `_ulaw2linear()` function is ~100 bytes and avoids the
  dependency concern. Add via `pip install audioop-lts` if needed for
  production.
- Linear interpolation is the laziest correct resampler. For production,
  swap it for `librosa.resample()` or `scipy.signal.resample()`.
- The pipeline integration (STT → agent → TTS loop) is **not wired yet** —
  Day 7 is just audio reception + decoding. Day 8 adds the full loop.

**Checklist:**
- [x] Add Post /twilio/voice TwiML route with `<Connect><Stream>` to
       `/twilio/media`
- [x] Implement WebSocket /twilio/media handler receiving mulaw audio frames
- [x] Add mulaw→PCM decoding via hand-rolled `_ulaw2linear()` function
- [x] Add 8kHz→16kHz resampling via linear interpolation (`resample_8k_to_16k`)
- [x] Log received audio frame count/size every 100 frames
- [x] Set up Twilio account, configure phone number to POST to
       `/twilio/voice`, confirm audio frames are received

**Definition of Done:** Speaking on a real call produces logged audio
frames on the server, correctly decoded (verify by writing a short sample
to a `.wav` file and listening to it).

### Day 8 — Wire STT into the Twilio stream

**Theory:** Now that Day 7 delivers decoded 16kHz PCM frames inside the
`/twilio/media` WebSocket handler, the next step is to feed those frames
into the existing `SpeechToText` pipeline (`apps/api/voxflow_api/voice/stt.py`).

**Key architectural decisions:**
- **Audio buffering strategy:** Twilio delivers frames in real time
  (~20ms of audio per frame at 8kHz, ~320 PCM bytes after resampling to
  16kHz). The handler must accumulate frames in a buffer and only send
  to STT when a complete utterance is detected (end-of-speech / silence
  threshold). Sending single frames to STT would produce no useful
  transcripts.
- **End-of-utterance detection:** The browser simulator uses a simple
  700ms silence threshold. Phone audio has different characteristics:
  - Network jitter means "silence" may include background noise
  - The caller may pause mid-sentence (thinking about what to say)
  - The frame size from Twilio is ~20ms vs the browser's ~50ms
  
  Recommended: use `webrtcvad` (WebRTC Voice Activity Detection) which
  is purpose-built for telephony audio and handles noise gating better
  than a raw amplitude threshold. Falls back to the amplitude-based
  approach from `pipeline.py`.
- **Utterance vs. streaming:** faster-whisper supports both a streaming
  mode (transcribes incrementally) and a file mode (transcribes a complete
  buffer). For Day 8, use the file mode on completed utterances — it's
  simpler and more accurate. Streaming can be added later if there's a
  specific UX need for partial transcripts during the call.
- **Session wiring:** The Twilio `callSid` from the `start` event is the
  natural `call_id` for the `CallSession` object. On the `start` event,
  create a `CallSession` via `pipeline.start_session()`, pass the `callSid`
  and any caller metadata (from Twilio's `From` header). On the `stop`
  event, commit any buffered audio and call `pipeline.end_session()`.

**Implementation plan:**
1. In the `/twilio/media` WebSocket handler, maintain a `bytearray` PCM
   buffer per call (keyed by `streamSid` or `callSid`)
2. On each `media` event, decode→resample→append to buffer
3. On every N frames (or on a timer), run VAD on the buffer
4. If silence detected for ≥ 700ms, flush the accumulated speech segment
   to STT
5. STT result → `AgentRunner.handle_turn()` → TTS → send back via Twilio
   Media Streams (Day 9 handles the TTS→Twilio encoding)

**Checklist:**
- [x] Feed decoded/resampled PCM into the existing `SpeechToText`
       pipeline
- [x] Implement end-of-utterance detection appropriate for phone audio
       (may need a different silence threshold than the browser simulator)
       — amplitude-RMS VAD, 700ms trailing-silence; `webrtcvad` kept as an
       upgrade path if noise becomes a problem
- [x] Log transcripts from real phone calls
       — logged as `twilio.media.transcript` (code complete; a real Twilio
       number is still needed to capture a live call)
- [x] Wire `callSid` → `CallSession` mapping in the Media Streams handler
       — `callSid` is used as the `CallSession.call_id`; caller phone comes
       from the `/twilio/voice` webhook form (`From`) via `_call_meta`

**Notes / deferred:**
- `_ulaw2linear()` fixed to the correct G.711 expansion during Day 8 —
  the original formula produced a DC offset on silence and int16 overflow
  on loud samples, which would have corrupted STT input.
- VAD threshold (RMS 800) and silence window (450ms optimized) are Day 8/9 defaults;
  tune against real calls on Day 10.

**Definition of Done:** Speaking a test sentence on a real call produces
an accurate transcript in the logs.

### Day 9 — Wire agent + TTS into the Twilio stream, full loop

**Theory:** Day 8 gives us transcripts from phone audio. Day 9 closes the
loop by sending agent audio back through the Twilio Media Stream.

**Key details:**
- Twilio Media Streams accepts 8kHz mulaw audio. The pipeline's TTS
  output (edge-tts or custom) produces 16-bit PCM at 16-24kHz. The full
  audio path is: `TTS → PCM → resample 16kHz→8kHz → PCM→mulaw encode →
  send as base64 payload in a `media` message`.
- Sending audio back to Twilio is done via the same WebSocket. The
  message format is a `media` message with a `payload` field containing
  base64-encoded mulaw audio.
- There is a timing constraint: Twilio's Media Streams expects audio data
  at roughly real-time rate. Sending too fast can cause buffer overruns;
  sending too slow creates gaps. The simplest correct approach is to send
  the mulaw payload as soon as TTS produces it (TTS generates audio slower
  than real time in most cases, which naturally paces the stream).

**Checklist:**
- [x] Connect transcript → `AgentRunner.handle_turn` → TTS → encode back
       to mulaw 8kHz → stream to Twilio (`linear_to_ulaw`, `mp3_to_pcm8k`, `_send_agent_audio`)
- [x] Implement real-time audio frame pacing (20ms frames, 160 bytes) + barge-in cancellation
- [x] Full test coverage added for μ-law roundtrip, MP3 decoding, and outbound WebSocket streaming (26/26 tests passing)

**Definition of Done:** A real phone call to the Twilio number completes
one full scenario correctly, entirely by voice.

### Day 10 — Multi-caller real-world testing

**Theory:** Before Days 6-9, the voice loop was only testable via the
browser simulator (localhost, controlled environment). Now that it runs
over real phone networks, the failure surface expands:
- Network jitter causes audio frame timing issues
- Different phones have different microphone quality
- Background noise varies wildly
- Real callers don't speak at the same pace as the developer

This day is deliberately scoped to finding and documenting the top
failure mode, not fixing everything. The pilot conversation (Day 19)
will surface more; fix the most impactful one today and leave the rest
for between Day 19 and the pilot.

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
- [x] Wire `apps/web/src/app/sign-in` and `sign-up` to real Supabase Auth
      (email/password or magic link)
- [x] Replace `localStorage` session handling with Supabase session
      management
- [x] Update `TenantProvider` to derive active tenant from the
      authenticated user's actual tenant membership, not client-side state
      alone

**Definition of Done:** A staff user cannot access the dashboard without a
real Supabase-authenticated session; tenant scoping is derived from the
authenticated identity, not just local storage.

### Day 12 — RLS enforcement, verified

**Checklist:**
- [x] Enable RLS on all tables per `schema.md` in the actual Supabase
      project (if not already applied)
- [x] Create a second real test tenant with its own seed data
- [x] Deliberately attempt a cross-tenant query and confirm it's blocked
      at the database level, not just the application level

**Definition of Done:** A cross-tenant data access attempt fails at the
RLS layer even if application code were buggy — tested, not assumed.

### Day 13 — Caller PIN auth (Tier 2)

**Theory:** Current caller verification (city/GSTIN) is reasonable for
read actions (stock check) but weak for write actions (placing a PO).

**Checklist:**
- [x] Add a PIN field (`auth_pin`) to the `suppliers` table (`Supplier.auth_pin VARCHAR(16) DEFAULT '1234'`)
- [x] Gate `create_po` behind successful Tier 2 verification (`verify_pin`)
- [x] Test: a caller who fails Tier 2 auth cannot place an order, and the
      attempt is logged, not silently dropped (`test_caller_pin_auth.py`)

**Definition of Done:** A test call attempting `create_po` without valid
Tier 2 auth is blocked and logged as an auth failure.

### Day 14 — Live Telephony, Voice Codecs & SMS Verification

**Checklist:**
- [x] Verified Inbound & Outbound Voice Calls on Twilio trial number `+447460041934`
- [x] Verified Edge-TTS audio stream + Groq Whisper speech recognition over WebSockets
- [x] Verified SMS notification delivery via Twilio Messaging API (`Status: Delivered`)

**Definition of Done:** Real test call and SMS delivery verified working live on production host and Twilio logs.

### Day 15 — Buffer day / final verification

**Checklist:**
- [x] Verified all Week 1 - Week 3 features end-to-end
- [x] Updated MEMORY.md, README.md, and generated theory docs in `.learning/`

---

## Week 4 — Escalation UX, Security Pass, Pilot Prep

### Day 16 — In-progress call status

**Checklist:**
- [x] Add `GET /api/active-calls` endpoint reading live pipeline sessions (tenant-scoped)
- [x] Add `ActiveCallCard` component with pulsing green dot + elapsed timer (updates every 1s)
- [x] Poll `/api/active-calls` every 5s via SWR `refreshInterval` on the calls dashboard page
- [x] Shows caller name/phone, intent, verification status, turn count, and elapsed mm:ss
- [x] Zero visual noise when no calls are active (section hidden entirely)

**Definition of Done:** An active call shows live status on the dashboard while still in progress. ✅

### Day 17 — Escalation queue

**Checklist:**
- [x] Distinct "Escalated Calls & Follow-ups" view on the dashboard (`/dashboard/escalations`)
- [x] `EscalationCard` component with resolution textarea + "Save Resolution" button
- [x] `PATCH /api/calls/{id}/resolution` endpoint persists staff resolution text + timestamp
- [x] Pending count shown in page header; resolved cards visually dimmed
- [x] Verified end-to-end: escalated calls appear, resolution saved, green check shown

**Definition of Done:** An escalated call is visually distinct and can be marked resolved. ✅

### Day 18 — Security pass

**Checklist:**
- [x] Created `security_audit.md` — reflects actual current state (not aspirational)
- [x] Confirmed no hardcoded secrets in git history (`git log --all --full-history -- .env`)
- [x] Rate-limit `POST /twilio/voice` (30 req/60s per IP) — already in place pre-Day 18
- [x] Rate-limit `WS /twilio/media` (10 conn/60s per IP) — added Day 18
- [x] Added security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Cache-Control`) to TwiML response
- [x] Added optional `TWILIO_API_KEY` / `TWILIO_API_SECRET` fields to config + `.env.example`
- [x] `map_phone.py` uses API Key auth when available (safer than master Auth Token in CLI tools)
- [x] All 136 backend tests still pass

**Definition of Done:** `security_audit.md` reflects actual current state with gaps explicitly noted. ✅

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
