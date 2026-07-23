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
| STT | `faster-whisper` (local) | Cloud STT APIs, unless a specific accuracy problem is proven first |
| TTS | `edge-tts` | ElevenLabs, unless a specific quality problem is proven first — edge-tts is free and already integrated |
| Telephony | Twilio (Voice + Media Streams) | Do not evaluate alternatives (Vonage, Plivo, etc.) until Twilio is proven insufficient |
| Database | Supabase Postgres | Do not migrate vendors — see ARCHITECTURE.md section 2 |
| Frontend | Next.js 14, Tailwind, existing component set | Do not introduce a second UI framework or CSS system |
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
- **Do not build outbound calling, payment processing, or CRM features**
  — explicitly out of scope per PRD.md section 6.
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
- Every new DB table must include `tenant_id` with a foreign key to
  `tenants.id`, and get an RLS policy added to `schema.md`
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
- **Multi-tenancy is non-negotiable.** Any AI-generated code that touches
  a business table without `tenant_id` scoping should be rejected on
  review, no exceptions, no "I'll fix it later."

## 5. When to Deviate From This Document

If a rule here turns out to be wrong once real Twilio integration or a
real pilot conversation happens, update RULES.md explicitly and note the
date and reason — don't silently work around it in code.
