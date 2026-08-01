# VoxFlow — Memory / Live Status

**Purpose:** The single source of truth for "where are we right now."
Update this at the end of every work session — before closing your editor,
not "later." If this file is stale, every other planning doc becomes
unreliable.

---

## Current Position

**Last updated:** 2026-08-01
**Currently on:** Week 2 — Day 8 complete: STT wired into Twilio Media Stream (audio buffer → VAD → SpeechToText → agent → TTS, transcripts logged).
**Currently being worked on:** Day 9 — Stream agent TTS audio back to Twilio (encode → mulaw 8kHz → send `media` messages).

## What's Actually Done (verified against the real repo)

- ✅ FastAPI backend skeleton with working agent loop (`AgentRunner`)
- ✅ Pluggable LLM providers: Groq, Ollama, OpenRouter
- ✅ 11 agent tools implemented and tested via browser simulator:
  `lookup_supplier`, `verify_caller`, `check_stock`, `get_shipment_status`,
  `create_po`, `verify_po`, `schedule_appointment`, `send_email`,
  `send_whatsapp_message`, `update_worksheet`, `type_notes`,
  `escalate_to_human`
- ✅ Multi-tenant schema with `tenant_id` on all business tables
  (`schema.md`)
- ✅ RLS policy blueprint written (not yet confirmed applied/tested against
  a real second tenant — see Week 3 Day 12)
- ✅ Local STT (faster-whisper) and TTS (edge-tts) working through the
  WebSocket-based browser phone simulator
- ✅ Next.js 14 dashboard with pages: calls, orders, shipments, stock,
  suppliers, appointments, communications, simulator, pricing, sign-in/up
- ✅ Multi-tenant switcher on the dashboard (demo companies: Varun
  Beverages, Amul, Haldirams, Britannia)
- ✅ Dark neon design system implemented in Tailwind config + globals.css
- ✅ Security audit written for input sanitization, SQL injection
  prevention, secret management, WebSocket security (`security_audit.md`)
- ✅ Backend circular import resolved & test suite verified passing (15/15 unit/integration tests passing cleanly)
- ✅ **Async DB layer** — all agent tool functions use async SQLAlchemy engines (aiosqlite for dev, asyncpg for prod). DB calls no longer block the event loop.
- ✅ **TTL cache** — `check_stock` and `lookup_supplier` reads cached in-process (30s TTL). Stock cache invalidated on `create_po` writes.
- ✅ **Security pass** — live API keys removed from `.env` files, `.env.example` files cleaned, sensitive deps excluded from test path.
- ✅ **Timing logs added** — STT, TTS, tool execution, and DB persist all logged with millisecond precision; LLM timing was already present in `runner.py`.
- ✅ **Day 6 — Twilio webhook skeleton** — `POST /twilio/voice` returns TwiML with `<Connect><Stream>` pointing to WebSocket route.
- ✅ **Day 7 — Media Streams WebSocket** — `/twilio/media` receives mulaw 8kHz frames, decodes to PCM via `_ulaw2linear()`, resamples to 16kHz via linear interpolation, logs frame stats. Requires Twilio account to test end-to-end.
- ✅ **Day 8 — STT wired into Twilio stream** — per-call PCM buffer keyed by `callSid`, amplitude-RMS VAD (speech threshold 800, 700ms trailing silence = utterance end), flushes each utterance into `pipeline.commit_audio()` (STT → agent → TTS) via a background task, logs `twilio.media.transcript`. Caller phone captured from the `/twilio/voice` webhook form and wired into the `CallSession`. **Bug fixed:** `_ulaw2linear()` was using a wrong G.711 expansion formula (silence decoded to a 528 DC offset; loud samples overflowed int16) — corrected to the standard `((2*mantissa+33)<<exponent)-33` then `<<2`, verified against known G.711 codeword values. Tests: 23/23 passing (8 new Twilio tests incl. an end-to-end WebSocket VAD→flush test with a fake pipeline).

## What's Known to Be Incomplete or Wrong

- ❌ **Latency baseline not yet measured** — timing logs are in place but need 5 test conversations run through the simulator to get real numbers (Week 1 Day 4)
- ❌ **Twilio phone number not yet configured** — Media Streams WebSocket route (`/twilio/media`) and TwiML endpoint (`/twilio/voice`) are implemented, but need a real Twilio account + phone number to test (Week 2 Day 6)
- ❌ **Agent audio not streamed back to Twilio** — Day 8 stores the agent turn (`last_turn` with `agent_audio_b64`) but does not encode it to mulaw 8kHz and send it back — Day 9
- ❌ **VAD threshold not tuned on real calls** — amplitude RMS threshold (800) and 700ms silence are Day 8 defaults; needs real multi-caller testing (Day 10) to tune
- ❌ **Staff auth is `localStorage`-based**, not real Supabase Auth (Week 3
  Day 11)
- ❌ **Caller auth is city/GSTIN only** — no PIN/stronger verification for
  write actions like `create_po` (Week 3 Day 13)
- ❌ **No dashboard realtime** — call logs don't update live without a
  manual refresh (Week 3 Day 14)
- ❌ **No real pilot conversation has happened** — the target workflow
  (Varun Beverages / PepsiCo distributor) is a secondhand hypothesis, not
  validated (see PRD.md section 0 and Week 4 Day 19)
- ❌ **No confirmed backend hosting** — README mentions Railway as an
  example, not finalized

## Latency Baseline

*(To be filled in during Week 1 Day 4 — do not skip this, it's the only
way to know if the async DB fix and caching actually helped.)*

- STT: —
- LLM per iteration: —
- DB call (pre-fix): —
- DB call (post-fix): —
- TTS: —

## Decisions Log

*(Add an entry whenever a real architectural or product decision gets
made — especially anything that deviates from RULES.md or ARCHITECTURE.md
as written. Keep entries short.)*

- 2026-07-23 — Decided to stay on Supabase Postgres rather than migrate to
  Neon; latency concern was diagnosed as a synchronous-DB-call architecture
  issue, not a vendor issue. See ARCHITECTURE.md section 2.
- 2026-07-25 — Twilio Media Streams route created as a separate file
  (`routes/twilio.py`) rather than merged into `routes/ws.py`; the browser
  simulator and Twilio stream share the same pipeline but have different
  wire formats (WebSocket message protocol), justifying separate route
  files.
- 2026-07-25 — Frontend double-Topbar bug: `DashboardLayout` rendered a
  `<Topbar>` but each child page also imported `<Topbar>`. Fixed by replacing
  per-page Topbar imports with inline page headers — keeps layout's global
  Topbar (brand, company selector, search, user menu) while showing
  page-specific titles.

## Day 8 Prep (Next Session)

1. Wire STT into Twilio stream — **done (2026-08-01)**, see PHASES.md Day 8
2. Encode the stored agent turn (`st.last_turn["agent_audio_b64"]`, MP3 from edge-tts) → decode to PCM → resample to 8kHz → mulaw encode → send as base64 `media` messages back through the same WebSocket — Day 9
3. Real Twilio phone number still required to test end-to-end (Day 6/7/8 all tested via unit tests + a fake-pipeline WebSocket test, not a real call)
4. See `.learning/day-08-stt-into-twilio-stream.md` for the completed record
