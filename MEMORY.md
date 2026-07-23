# VoxFlow — Memory / Live Status

**Purpose:** The single source of truth for "where are we right now."
Update this at the end of every work session — before closing your editor,
not "later." If this file is stale, every other planning doc becomes
unreliable.

---

## Current Position

**Last updated:** 2026-07-23 (revised)
**Currently on:** Week 1 complete — Days 1-5 marked done. Timing logs added.
**Currently being worked on:** Nothing actively in progress (Week 2 next)

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

## What's Known to Be Incomplete or Wrong

- ❌ **Latency baseline not yet measured** — timing logs are in place but need 5 test conversations run through the simulator to get real numbers (Week 1 Day 4)
- ❌ **No real telephony** — calls only work through the browser simulator,
  not an actual phone number (Week 2)
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

## Next Session Should Start With

1. Read this file first
2. Read PHASES.md, find the first unchecked `- [ ]` item
3. Read RULES.md if touching anything infra/library-related
4. Do the work
5. Update this file before ending the session — new "What's Actually
   Done," update "Currently on," add a Decisions Log entry if applicable
