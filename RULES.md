# VoxFlow — Development Rules

**Purpose:** What to use, what to avoid, and the boundaries for any AI
coding assistant (Claude Code, Antigravity, Cursor, etc.) working on this
repo. Read this before starting any day's work in PHASES.md.

---

## 1. Libraries — Use These

| Purpose | Library | Do not substitute with |
|---|---|---|
| Backend framework | FastAPI | Flask, Django (inconsistent with existing async design) |
| ORM | SQLAlchemy 2.0 (moving to async engine) | raw `psycopg2` string queries, Django ORM |
| LLM access | `openai`-compatible SDK against Groq/Ollama/OpenRouter | LangChain, LangGraph as a dependency — the existing `agent/runner.py` already implements the pattern LangGraph would give you; do not add the framework on top of a hand-rolled version of the same thing |
| STT | **Groq hosted `whisper-large-v3-turbo`** (`STT_PROVIDER=groq`) | Do not make a local model the default again — see the 2026-08-02 deviation in §5. `faster-whisper` stays available as `STT_PROVIDER=local` for offline dev only. |
| TTS | `edge-tts` | ElevenLabs, unless a specific quality problem is proven first — edge-tts is free and already integrated |
| Telephony | Twilio (Voice + Media Streams) | Do not evaluate alternatives (Vonage, Plivo, etc.) until Twilio is proven insufficient |
| Database | Supabase Postgres | Do not migrate vendors — see ARCHITECTURE.md section 2 |
| Frontend | Next.js 16, Tailwind, existing component set | Do not introduce a second UI framework or CSS system |
| Auth | Supabase Auth (once implemented) | Do not build custom JWT/session handling from scratch |

## 2. Explicitly Avoid

- **Do not add LangGraph, LangChain, CrewAI, or any agent framework.**
  `agent/runner.py` already implements a tool-calling loop with a max
  iteration guard. Adding a framework on top adds a dependency and a
  learning curve without adding capability at this stage.
- **Do not introduce a second database** (e.g. MongoDB for "flexible"
  call logs) — everything fits in Postgres with JSON columns, which is
  already the pattern used (`items_json`, `transcript_json`, etc.)
- **Do not switch database vendors** to solve a latency problem — see
  ARCHITECTURE.md section 2. The fix is async DB calls + caching, not a
  vendor swap.
- **Do not add authentication complexity beyond what's needed.** Two
  auth systems exist by design: staff login (Supabase Auth) and caller
  verification (phone + city/GSTIN, later PIN). Do not conflate them or
  build a third system.
- **Do not build outbound cold calling, payment processing, or generic CRM features.** Controlled operational campaigns already exist, but their worker remains globally disabled in production and they must obey `ARCHITECTURE.md` policy, consent, idempotency, and canary rules. Never add an inline provider call to an API request path.
- **Do not commit `.env` files, API keys, or Supabase service role keys.**
  `.gitignore` already excludes these — verify before every commit,
  don't assume.
- **Do not write raw SQL string interpolation.** Use SQLAlchemy's
  parameterized queries (`select(...)`, `.where(...)`) as already done
  throughout `tools.py` — this is a hard rule per `security_audit.md`.

## 3. Code Conventions

- Python: follow existing style in `apps/api` — type hints on every
  function signature, `from __future__ import annotations`, `ruff` for
  linting (already in `requirements.txt`)
- Every new agent tool must: (a) accept `session: CallSession` as first
  arg, (b) scope every DB query by `session.tenant_id`, (c) return a
  plain `dict[str, Any]`, (d) be registered in both `execute_tool()`
  dispatcher and `TOOL_DEFINITIONS` schema in `tools.py`
- Every new tenant-owned DB table must include `tenant_id` with a foreign key to `tenants.id`, production migration coverage, tenant-safe query/read handling, and a `schema.md` update. Tables reached only through a tenant-owned parent must document that ownership explicitly.
- Frontend: follow existing dark-neon design system (see DESIGN.md) —
  do not introduce new color values outside the existing Tailwind config
  without updating DESIGN.md first

## 4. AI Assistant Boundaries

When using Claude Code, Antigravity, or any AI pair-programmer on this
repo:

- **Work one phase/day at a time**, per PHASES.md. Do not let the
  assistant "helpfully" implement Phase 4 features while working on
  Phase 2 — this is how scope creep and untested code pile up.
- **Do not let the assistant invent new architecture** (new services, new
  databases, new frameworks) without it being reflected here in RULES.md
  and ARCHITECTURE.md first. If the assistant proposes something outside
  these docs, stop and update the docs deliberately before proceeding —
  don't let undocumented decisions accumulate in code only.
- **Require the assistant to update MEMORY.md** at the end of any session
  where files were changed — what was completed, what's in progress,
  what's broken.
- **Do not let the assistant mark a Definition of Done as met without
  actually running the test/check described in PHASES.md.** "This should
  work" is not the same as verified.
- **Secrets:** never paste real API keys into a prompt to an AI assistant
  if that conversation could be logged or shared. Use `.env.example`
  placeholders when discussing config.
- **Multi-tenancy is non-negotiable.** Any AI-generated code that touches a business, job, provider-operation, preference, reservation, or policy-audit record without tenant scoping should be rejected on review, no exceptions, no "I'll fix it later."
- **Outbound side effects are non-negotiably gated.** Any campaign change must preserve transactional enqueue, provider-operation idempotency, tenant policy before reservation, no-redial reconciliation, and the production kill switch. Tests and browser checks must use mocked providers or dry run.

## 5. When to Deviate From This Document

If a rule here turns out to be wrong once real Twilio integration or a
real pilot conversation happens, update RULES.md explicitly and note the
date and reason — don't silently work around it in code.

### Logged deviations

**2026-08-02 — STT moved from local `faster-whisper` to Groq hosted Whisper.**

The original rule said "cloud STT only if a specific accuracy problem is
proven first." The problem that actually forced the change was latency and
hosting cost, not accuracy:

- A `base` model on a small cloud CPU took 1.5-3s per utterance. Added to LLM
  and TTS time, that put 4-6s of silence between the caller finishing a
  sentence and the agent replying. On a phone call, silence reads as a dropped
  line — this is the single most damaging failure mode the product has.
- The local model forced ~2GB of RAM and a ~2.5GB image, which ruled out every
  free-tier host and made always-on hosting a paid requirement. Always-on is
  non-negotiable for inbound telephony: a sleeping backend is a missed call.

Groq's `whisper-large-v3-turbo` returns in ~200-400ms, is free at pilot volume,
and reuses the Groq key already in use for the LLM. The image drops to ~250MB.

`faster-whisper` was not deleted — it is still selectable via
`STT_PROVIDER=local` and lives in `requirements-local.txt`. The STT layer is
now a provider factory mirroring the existing LLM factory, so switching back
is a one-line env change.

**Constraint that drove this:** the project owner requires everything to run
server-side with nothing depending on a local machine.

**2026-08-21 — Free-tier demonstration hosting for initial stages.**

The project owner has specified that the initial stages must remain on free-tier
infrastructure. Fly is therefore configured for automatic stop and automatic
wake-up (`auto_stop_machines = 'stop'`, `min_machines_running = 0`) rather than
persistent availability. This allows safe dashboard and simulator demonstrations
following a warm-up request, but it is not suitable for real inbound telephony,
continuous worker operation, or a production pilot SLA. Those workloads remain
disabled until the owner explicitly chooses a paid, always-on deployment.

This supersedes the earlier server-only hosting constraint **only for the
initial, demonstration stage**. It does not weaken tenant isolation, callback
verification, campaign gates, provider safeguards, or the production kill
switch.
