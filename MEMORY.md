# VoxFlow — Memory / Live Status

**Purpose:** The single source of truth for "where are we right now."
Update this at the end of every work session — before closing your editor,
not "later." If this file is stale, every other planning doc becomes
unreliable.

---

## Current Position

**Last updated:** 2026-08-02
**Currently on:** Inbound customer-support call flow is built and tested. The
product now answers "have you signed our PO / what quantity / when did you send
it / where has it reached", verifies who is asking before disclosing anything,
and logs the outcome to Google Sheets.
**Next action:** Deploy to Oracle Cloud following `SETUP.md`, then **make one
real phone call**. Nothing further in Weeks 2-4 should start before that.

## Scope change (2026-08-02)

Originally scoped as *distributor ops* — suppliers ringing in to place POs and
check stock. Now scoped as **inbound B2B customer support**: our customers ring
in about orders they have already placed with us. The `suppliers` table carries
a `contact_type` column (`customer` | `supplier` | `both`) and serves both
sides. Stock-check and PO-creation tools are retained but are no longer the
primary flow.

## What's Actually Done (verified against the repo — 60/60 tests passing)

### Core (pre-existing)
- ✅ FastAPI backend, async SQLAlchemy throughout, TTL cache on hot reads
- ✅ Agent tool-calling loop (`AgentRunner`), pluggable LLM providers
- ✅ Next.js 14 dashboard, dark neon design system, tenant switcher
- ✅ Twilio Days 6-9: TwiML webhook, Media Streams receive, mulaw↔PCM, VAD,
  STT flush, agent audio streamed back with 20ms pacing + barge-in

### Customer-support flow (2026-08-02)
- ✅ **15 agent tools** — added `check_po_status`, `get_order_details`,
  `log_call_outcome` to the existing 12
- ✅ **Two-factor caller verification.** `verify_caller` requires company
  **plus** one of {city, GSTIN, contact name}, tolerates speech-to-text noise
  ("Pvt. Ltd." vs "Pvt Ltd", spaced-out GSTINs), caps attempts at 3, and
  escalates on lockout. No order data is disclosed until `session.verified`.
- ✅ **Schema:** `orders` gained `customer_po_ref`, `po_signed`,
  `po_signed_at`, `po_signed_by`, `dispatched_at`. `calls` gained `reason`,
  `solution`, `resolution_status`, `satisfaction`, `follow_up_required`,
  `staff_resolution`, `staff_resolved_at`, `sheet_synced`, `verified`. New
  `tenant_phone_numbers` table. Idempotent migration in
  `migrations/001_customer_support_flow.sql`.
- ✅ **Google Sheets call log** — async, non-blocking, structurally unable to
  fail a live call (`integrations/gsheets.py`). Postgres is the source of
  truth; Sheets is the ops-facing mirror.
- ✅ **Abandoned-call fallback** — a caller who hangs up mid-verification still
  produces an `unresolved` row flagged for follow-up.
- ✅ **System prompt rewritten** for customer support: verification-first,
  mandatory outcome logging, explicit instruction to log honestly rather than
  flatteringly.
- ✅ Dashboard: outcome columns + satisfaction badges on the calls page; new
  `/dashboard/escalations` view with a staff resolution field
  (`PATCH /api/calls/{id}/resolution`).

### Infrastructure (2026-08-02)
- ✅ **STT moved server-side to Groq** `whisper-large-v3-turbo`. ~200-400ms vs
  1.5-3s locally; image ~250MB vs ~2.5GB. `faster-whisper` still selectable via
  `STT_PROVIDER=local` + `requirements-local.txt`. See RULES.md §5.
- ✅ **Tenant resolved from the dialed number** via `tenant_phone_numbers`.
  `routes/twilio.py` previously had *no* tenant handling — every inbound call
  landed on the default tenant.
- ✅ **Twilio signature validation** + per-IP rate limiting on the public
  webhook.
- ✅ **Oracle Cloud Always Free deploy** — `deploy/docker-compose.prod.yml`
  plus Caddy for automatic TLS. Multi-stage non-root Dockerfile, ARM64-ready.
- ✅ **`SETUP.md`** — complete walkthrough from zero to a live phone call.

### Bugs found and fixed
- ✅ **Calls were never persisted when the caller hung up mid-reply.**
  `_finalize_stream` cancelled the outbound-audio task and awaited it inside a
  bare `except Exception`; `asyncio.CancelledError` inherits from
  `BaseException`, so it escaped and skipped `end_session()` entirely.
  Persistence now runs in a `finally` cancellation cannot bypass. This was
  silently losing exactly the calls most worth reviewing.
- ✅ Two Day 9 tests were broken: one called edge-tts over the network (so it
  failed offline and in CI), and one looped on `receive_text()` until it
  raised — but Starlette's TestClient never surfaces the server's close frame,
  so the whole suite hung indefinitely.

## What's Known to Be Incomplete or Wrong

- ❌ **No real phone call has been made.** Every layer is implemented and
  unit/integration tested, but nothing is proven against a live phone network.
  This is the single most important outstanding item.
- ❌ **VAD not tuned on real calls** — `_SILENCE_RMS = 800`, `_SILENCE_MS = 450`
  remain guesses until real callers are heard.
- ❌ **Latency baseline not measured end-to-end.** Timing logs exist; no real
  numbers yet. Expect roughly 1.0-1.5s per turn with Groq STT.
- ❌ **Staff auth is still `localStorage`-based**, not Supabase Auth (Week 3
  Day 11). Every `/api` endpoint therefore trusts a client-supplied
  `tenant_id` — acceptable for a single operator, not for a customer's staff.
- ❌ **RLS written but never verified** against a live second tenant (Week 3
  Day 12). Application-level scoping *is* enforced, with two cross-tenant
  isolation tests.
- ❌ **No dashboard realtime** — rows appear on refresh (Week 3 Day 14).
- ❌ **No caller PIN** for write actions (Week 3 Day 13). Read queries are
  gated by two-factor verification, which is proportionate; placing an order
  by phone is not.
- ❌ **No real pilot conversation** yet (Week 4 Day 19) — the workflow remains
  a hypothesis.
- ❌ **Groq free tier is rate-limited per minute.** Fine for a pilot; real
  volume needs the paid tier.

## Latency Baseline

*(Fill in after the first real calls. Groq STT should make this dramatically
better than the original local-Whisper estimates.)*

- STT (Groq, expected ~200-400ms): —
- LLM per iteration: —
- DB call: —
- TTS: —
- **Total per turn:** —

## Decisions Log

- 2026-07-23 — Stay on Supabase Postgres rather than migrate to Neon; the
  latency concern was a synchronous-DB-call architecture issue, not a vendor
  issue. See ARCHITECTURE.md §2.
- 2026-07-25 — Twilio Media Streams kept in a separate `routes/twilio.py`
  rather than merged into `routes/ws.py`; same pipeline, different wire format.
- 2026-07-25 — Fixed the frontend double-Topbar bug with inline page headers.
  **Do not reintroduce per-page `<Topbar>` imports.**
- 2026-08-02 — **Product rescoped** to inbound customer support (see above).
- 2026-08-02 — **STT switched to Groq hosted Whisper.** Documented deviation
  from RULES.md §1; rationale in RULES.md §5. Driven by the requirement that
  everything run server-side, and by phone-call latency.
- 2026-08-02 — **Backend host: Oracle Cloud Always Free**, chosen over Fly.io
  (~$2/mo) for genuine $0. Render free, Cloud Run and HF Spaces were rejected:
  they sleep when idle, and a sleeping backend is a missed call.
- 2026-08-02 — **Google Sheets is a mirror, not the source of truth.** Postgres
  holds the record; Sheets is written best-effort so an outage can never take
  down a phone call.

## Next Session

1. Work through `SETUP.md` end to end and make one real call. The Day 6 and
   Day 9 definitions of done in PHASES.md are still unmet — they were only ever
   unit-tested.
2. Record real latency numbers above.
3. Tune the VAD against real callers (Day 10).
4. Only then start Week 3 (Supabase Auth → RLS verification → realtime).
