# VoxFlow — Memory / Live Status

**Purpose:** The single source of truth for "where are we right now."
Update this at the end of every work session — before closing your editor,
not "later." If this file is stale, every other planning doc becomes
unreliable.

---

## Current Position

**Last updated:** 2026-08-13
**Currently on:** **Week 3 / Day 12 Complete.** Live telephony verified on real phone call with Twilio trial number `+447460041934` mapped to tenant `varun` ("Varun Beverages UK Support Line"). Supabase RLS database policies active across all 11 tables. Real Supabase auth integrated in web dashboard (`/sign-in`, `/sign-up`). Next up: Week 3 / Day 13 (Caller PIN auth for Tier 2 write operations).
**Deployed and self-test green.** Every component of a real call is verified working on the Oracle VM (`193.123.187.97`, `VM.Standard.E2.1.Micro`, 1 GB / 1-8th OCPU, uk-london-1) behind Caddy TLS at `https://voxflow-jeevesh.duckdns.org`. Supabase schema created from `migrations/000_base_schema.sql`, RLS on all 11 tables, demo data seeded.
Groq LLM + Groq STT + edge-tts + the full codec chain all pass.
**Next action:** point the Twilio number's voice webhook at
`https://voxflow-jeevesh.duckdns.org/twilio/voice`, insert the number into
`tenant_phone_numbers`, and **make one real phone call**. Nothing in
Weeks 3-4 should start before that call.

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
- ✅ **`SETUP.md`** — complete walkthrough from zero to a live phone call,
  corrected for the machine actually in use.
- ✅ **Audio codecs vectorised with numpy** — 17.1ms → 0.87ms of CPU per second
  of call audio (20x). Verified byte-identical across all 256 μ-law codewords
  and all 65536 int16 values. This is what makes a 1/8-OCPU instance viable
  after A1 capacity turned out to be unobtainable.
- ✅ **`scripts/preflight.sh`** — validates host, repo, `.env`, DNS and firewall
  before the build. Catches the 6543-vs-5432 pooler mistake, a trailing slash in
  `PUBLIC_BASE_URL`, `DOMAIN`/`PUBLIC_BASE_URL` mismatch, missing swap and closed
  iptables. Never prints secret values.
- ✅ **`python -m voxflow_api.selftest`** — exercises every component of a real
  call except Twilio's transport: config, DB + migration detection, LLM, TTS,
  the full codec chain, an **STT round-trip through the μ-law path**, and one
  complete agent turn with tool calls. Prints the per-turn latency baseline.
  Everything green ⇒ a failed call is Twilio configuration specifically.
- ✅ **Google Sheets write is now non-blocking.** It used to be awaited mid-call
  with a 10s HTTP timeout, so a slow Google response would have been heard by
  the caller as up to ten seconds of dead air. It now runs as a background task
  drained by `end_session()` after the caller hangs up, keeping `sheet_synced`
  accurate at zero cost to the caller. Timeout also cut to 6s.

### Bugs found and fixed
- ✅ **The app could not start against Postgres at all.** `db.py` builds a
  SYNCHRONOUS engine at import (the dashboard REST routes are sync), and
  SQLAlchemy imports the DBAPI eagerly at engine construction.
  `requirements.txt` declared `asyncpg` for the async engine but **no sync
  Postgres driver**, so importing `voxflow_api.db` against a `postgresql://`
  URL raised `ModuleNotFoundError: No module named 'psycopg2'`. Every module
  imports `db`, so the whole app died at startup — and because the crash was at
  *import* time, `python -m voxflow_api.selftest` printed nothing at all, which
  looked like a broken command rather than a broken deployment.
  **Why 86 tests missed it:** `conftest.py` pins every test to SQLite, which
  needs no driver. The Postgres path had zero coverage. Fixed by adding
  `psycopg2-binary`, converting the opaque ImportError into an actionable
  message naming both drivers, and adding `tests/test_db_drivers.py` — 10 tests
  that construct engines for the URLs we actually deploy with and spawn a
  subprocess to import the full app against Postgres. Verified by uninstalling
  psycopg2: 4 of the 10 fail, and pass again once restored.
  *Found by the Antigravity agent, not by this suite.*
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

- ✅ **Caller identification could match an arbitrary company** (2026-08-06).
  Three defects at once, all live while the self-test was green.
  (a) `lookup_supplier` stripped non-digits from the phone argument and matched
  `LIKE '%<digits>%'`. The model passed the literal string `"caller's phone
  number"` — because `caller_phone` was in *no* message sent to the LLM, while
  the prompt claimed "you already have it from the call metadata" — so the
  filter reduced to `LIKE '%'`, matching every supplier. `.first()` returned an
  arbitrary company and `session.supplier_id` was set to it, which is the
  record `verify_caller` checks against.
  (b) The result returned `city`, `gstin` and `contact_person` — the exact three
  values `verify_caller` accepts as its second factor. The model was shown the
  answers to its own security question and can pass back what it read instead of
  what the caller said, so two-factor verification was theatre.
  (c) The TTL cache keyed on (tenant, phone, name) but not verification state,
  so a verified call cached the full record and the next *unverified* caller was
  served it from cache. Found by the new tests, not by inspection.
  Fixed: fall back to `session.caller_phone`, never filter on <7 digits, withhold
  all three secrets until verified, add verification state to the cache key, add
  `session.identified_by_phone`, and inject a CALL CONTEXT system message with
  the real number. 19 regression tests in `tests/test_caller_identification.py`.
  **Lesson: the self-test was green through all of this.** It asserted that a
  tool was called, not that the right thing happened. Green means "nothing threw",
  never "the behaviour is correct".

## What's Known to Be Incomplete or Wrong

- ❌ **No real phone call has been made.** Every layer is implemented and
  unit/integration tested, but nothing is proven against a live phone network.
  This is the single most important outstanding item.
- ❌ **VAD not tuned on real calls** — `_SILENCE_RMS = 800`, `_SILENCE_MS = 450`
  remain guesses until real callers are heard.
- ✅ **Latency baseline measured** (2026-08-06, on the 1/8-OCPU box, callers in
  the UK, Supabase eu-west-1). *PHASES.md Week 1 Day 4 — previously outstanding.*

  | Stage | Cold (self-test) | Warm (in-call) |
  |---|---|---|
  | Speech-to-text (Groq whisper-large-v3-turbo) | 288ms | 288ms |
  | LLM single turn (Groq llama-3.3-70b) | 1975ms | **367ms** |
  | Text-to-speech (edge-tts, full sentence) | 1703ms | streams |
  | Database connect | 2815ms | pooled |

  The cold column is alarming and misleading. It includes client construction,
  TLS handshakes and connection-pool warm-up, all of which happen once per
  process, not once per turn. The number that matters is the warm agent turn
  logged during the conversational check: **367ms for the LLM**, giving roughly
  **1.0-1.2s per conversational turn** once TTS streaming is accounted for.
  That is inside the 1.0-1.5s the plan assumed, on the smallest instance Oracle
  offers.

  Re-measure against a real call — this is still a lab number.
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
- 2026-08-05 — **Shape: `VM.Standard.E2.1.Micro`** (1 GB, 1/8 OCPU). Ampere A1
  was out of capacity in every London AD across repeated attempts. Viable only
  because the audio codecs were vectorised first.
- 2026-08-05 — **Phone numbers:** UK (+44) for testing since the developer is
  UK-based and will test from a UK mobile. **+91 is unobtainable** without an
  Indian entity (TRAI requires local company + GST). For an Indian pilot the
  route is the distributor **forwarding their existing landline** to our number,
  which also keeps the number their callers already know. Production India means
  an Indian provider (Exotel / Ozonetel / Knowlarity / Plivo) and a new adapter
  beside `routes/twilio.py`; the pipeline and all 15 tools stay untouched.
- 2026-08-05 — **`SHEETS_ENABLED=false` is the default and a supported state.**
  Deferring Sheets loses nothing: outcomes are captured in full and persisted to
  Postgres regardless.
- 2026-08-05 — **Sheets writes are fire-and-forget during a call.** Dead air is
  the worst failure this product can have, and it must never be caused by a
  third party. If the process dies mid-write the row is still in Postgres with
  `sheet_synced=0` — recoverable and visible.

## Post-pilot backlog (deliberately NOT built yet)

Ideas that are sound but must wait until a real call has succeeded — per
RULES.md §4, one phase at a time.

- **Outbound webhook fan-out.** Fire one fire-and-forget POST on call end
  (`call_id`, company, reason, solution, resolution_status, satisfaction,
  escalated, order ref) and let Zapier / Make / n8n do the downstream work:
  append to Sheets, Slack the escalations, create a CRM task, email a digest.
  Chosen over putting Zapier MCP in the tool loop because (a) a Zapier hop is
  0.5-2s and would be heard as dead air, (b) Zapier's free tier is 100
  tasks/month — one per call — and Starter at ~$20/mo would be 4x the entire
  infra + Twilio bill, and (c) a third party has no business in the critical
  path of a live call. A webhook keeps VoxFlow free of Zapier auth entirely and
  lets new downstream apps be wired without touching this codebase again.
  Roughly 40 minutes with tests. One `WEBHOOK_URL` env var.
- **Apps Script Sheets writer** as an alternative to the service-account path,
  for anyone blocked by the `iam.disableServiceAccountKeyCreation` org policy
  (which Google now applies to new organisations by default). Runs as the sheet
  owner, so no service account and nothing for a policy to disable.
- Supabase Auth for staff (Week 3 Day 11) — currently `localStorage`.
- Verify RLS against a live second tenant (Week 3 Day 12). More pressing than it
  was: the Supabase project ref is in public git history at `93f5b04`.
- Dashboard realtime (Week 3 Day 14).
- Caller PIN for write actions (Week 3 Day 13).

## Next Session

1. Work through `SETUP.md` end to end and make one real call. The Day 6 and
   Day 9 definitions of done in PHASES.md are still unmet — they were only ever
   unit-tested.
2. Record real latency numbers above.
3. Tune the VAD against real callers (Day 10).
4. Only then start Week 3 (Supabase Auth → RLS verification → realtime).
