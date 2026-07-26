# VoxFlow — Memory / Live Status

**Purpose:** The single source of truth for "where are we right now."
Update this at the end of every work session — before closing your editor,
not "later." If this file is stale, every other planning doc becomes
unreliable.

---

## Current Position

**Last updated:** 2026-07-26
**Currently on:** Week 2 — Days 1-7 code complete. Twilio Media Streams wired. Frontend double-Topbar fixed.
**Currently being worked on:** Day 8 — Wire STT into Twilio stream (next).

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

## What's Known to Be Incomplete or Wrong

- ❌ **Latency baseline not yet measured** — timing logs are in place but need 5 test conversations run through the simulator to get real numbers (Week 1 Day 4)
- ❌ **Twilio phone number not yet configured** — Media Streams WebSocket route (`/twilio/media`) and TwiML endpoint (`/twilio/voice`) are implemented, but need a real Twilio account + phone number to test (Week 2 Day 6)
- ❌ **STT not wired into Twilio stream** — Day 8: need to connect decoded PCM → SpeechToText pipeline for real phone calls
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

1. Wire decoded PCM buffer → `SpeechToText` in `routes/twilio.py`
2. Implement VAD (voice activity detection) for phone audio — use amplitude threshold or `webrtcvad`
3. Create `CallSession` on Twilio `start` event, manage buffer per `callSid`
4. Log transcripts from real Twilio calls
5. See `NEXT.md` for full Day 8 theory and implementation plan
