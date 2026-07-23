# VoxFlow — Architecture

**Last updated:** 2026-07-23
**Scope:** Directs app flow, component boundaries, folder structure, and
the specific latency-sensitive design decisions for the voice path.

---

## 1. System Overview

```
                    Caller's Phone
                         │
                         ▼
              Twilio Voice (Media Streams / WebSocket)
                         │
                         ▼
         ┌───────────────────────────────────────┐
         │        FastAPI Backend (apps/api)       │
         │                                          │
         │  voxflow_api/voice/pipeline.py           │
         │    - Buffers PCM audio                   │
         │    - STT (faster-whisper, local)         │
         │         │                                │
         │         ▼                                │
         │  voxflow_api/agent/runner.py              │
         │    - LangGraph-style tool-calling loop    │
         │    - LLM (Groq / Ollama / OpenRouter)     │
         │         │                                │
         │         ▼                                │
         │  voxflow_api/agent/tools.py                │
         │    - lookup_supplier, check_stock, etc.   │
         │    - Reads/writes via db.py (SQLAlchemy)  │
         │         │                                │
         │         ▼                                │
         │  voxflow_api/voice/tts.py (edge-tts)      │
         └───────────────────────────────────────┘
                         │
                         ▼
              Postgres (Supabase, tenant-isolated via RLS)
                         │
                         ▼
         ┌───────────────────────────────────────┐
         │      Next.js 14 Dashboard (apps/web)     │
         │  Live call view, orders, stock, etc.     │
         │  Supabase client for auth + realtime     │
         └───────────────────────────────────────┘
```

## 2. The Latency-Critical Path

The single most important architectural constraint in this project: **every
second between the caller finishing a sentence and the agent starting to
speak is felt directly by a human on a phone call.** Unlike a chat UI, there
is no acceptable "spinner" — silence on a call reads as broken.

Current latency budget per turn (approximate, to be measured for real once
Twilio is wired in):

| Step | Est. latency | Notes |
|---|---|---|
| STT (faster-whisper, local) | 200-600ms | Runs in executor thread, non-blocking — already correct |
| LLM turn (Groq) | 300-800ms per iteration | Multiple tool calls = multiple iterations, compounds |
| DB round-trip per tool call | ??? | **Currently synchronous, blocks event loop — must fix** |
| TTS (edge-tts) | 200-500ms | Network call to Microsoft's edge service |

**The one architectural change that matters most:** move `db.py` from
synchronous SQLAlchemy (`create_engine`, `sessionmaker`) to the async
equivalent (`create_async_engine` with `asyncpg`, `async_sessionmaker`),
and make every tool function in `tools.py` an `async def` using `await
db.execute(...)`. Right now, `execute_tool()` runs synchronous DB calls
inside `async def handle_turn`, which blocks the event loop for the
duration of every DB call — this is the real latency risk, not the choice
of Postgres host.

**Secondary fix:** add a lightweight cache (in-process `dict` with TTL, or
Redis/Upstash if you want it shared across server instances) in front of
`check_stock` and `lookup_supplier` — these are read-heavy, low-change-
frequency queries and don't need a network round-trip on every single call.

**Do not** try to solve latency by switching database vendors (Supabase →
Neon or similar). Any hosted Postgres has the same network-round-trip
characteristic; the fix is architectural (async + caching), not a vendor
swap.

## 3. Multi-Tenancy

- Every business table has `tenant_id` (see `schema.md`)
- RLS policies enforce isolation at the database level — this is the last
  line of defense, not the only one
- Application-level enforcement: every tool function in `tools.py` takes
  `session: CallSession` which carries `tenant_id`, and every query is
  scoped by it — this pattern is already correctly followed, keep it
- The dashboard's `TenantProvider` (`apps/web/src/lib/tenant-context.tsx`)
  scopes all frontend data fetching to the active tenant

## 4. Folder Structure

```
voxflow-voice-agent/
├── PRD.md                      # product requirements
├── ARCHITECTURE.md             # this file
├── RULES.md                    # what to use, what to avoid, AI boundaries
├── PHASES.md                   # week-by-week, day-by-day build plan
├── DESIGN.md                   # color, type, visual language
├── MEMORY.md                   # live status — what's done, what's in progress
├── schema.md                   # DDL + RLS policy reference
├── docker-compose.yml
├── vercel.json
├── apps/
│   ├── api/                            # FastAPI backend
│   │   ├── voxflow_api/
│   │   │   ├── agent/
│   │   │   │   ├── runner.py           # conversation loop, tool-calling
│   │   │   │   ├── tools.py            # all agent tools + DB access
│   │   │   │   └── prompts.py          # system prompt construction
│   │   │   ├── llm/
│   │   │   │   ├── factory.py          # provider selection
│   │   │   │   ├── groq.py / ollama.py / openrouter.py
│   │   │   │   └── base.py             # shared ChatTurn / response types
│   │   │   ├── voice/
│   │   │   │   ├── pipeline.py         # call session + turn orchestration
│   │   │   │   ├── stt.py              # faster-whisper wrapper
│   │   │   │   └── tts.py              # edge-tts wrapper
│   │   │   ├── routes/
│   │   │   │   ├── ws.py               # WebSocket call endpoint
│   │   │   │   └── data.py             # REST endpoints for dashboard
│   │   │   ├── db.py                   # SQLAlchemy models + session mgmt
│   │   │   ├── config.py               # env-driven settings
│   │   │   ├── schemas.py              # Pydantic request/response models
│   │   │   ├── seed.py                 # demo data seeding
│   │   │   └── verify_db.py            # DB health check script
│   │   ├── tests/
│   │   └── requirements.txt
│   └── web/                            # Next.js 14 dashboard
│       └── src/
│           ├── app/
│           │   ├── dashboard/
│           │   │   ├── calls/ orders/ shipments/ stock/
│           │   │   ├── suppliers/ appointments/ communications/
│           │   │   └── simulator/                # browser phone simulator
│           │   ├── sign-in/ sign-up/ pricing/ about/
│           │   └── layout.tsx / page.tsx
│           ├── components/                        # Nav, Sidebar, Topbar, Footer
│           └── lib/
│               ├── supabase/           # client + server Supabase clients
│               ├── tenant-context.tsx  # active tenant state
│               ├── theme-context.tsx   # dark/light mode
│               └── api.ts / types.ts
├── packages/core/                      # shared types/logic (currently minimal)
└── .planning/                          # historical phase tracking
```

**Rule of thumb going forward:** anything voice/agent-logic-related goes in
`apps/api/voxflow_api/`; anything dashboard/UI goes in `apps/web/src/`;
anything shared between the two (types, constants) should move into
`packages/core` rather than being duplicated.

## 5. Tech Stack (current, confirmed from repo)

| Layer | Choice | Status |
|---|---|---|
| Backend framework | FastAPI 0.115 | ✅ in place |
| ORM | SQLAlchemy 2.0 (sync) | ⚠️ needs async migration |
| Database | Supabase Postgres (prod) / SQLite (dev) | ✅ keep, fix async layer |
| LLM | Groq (Llama 3.1), Ollama, OpenRouter (pluggable) | ✅ in place |
| STT | faster-whisper (local, CPU) | ✅ in place |
| TTS | edge-tts | ✅ in place |
| Telephony | — | ❌ not started, Phase 3 |
| Frontend | Next.js 14, Tailwind | ✅ in place |
| Auth (staff) | localStorage session (temporary) | ⚠️ needs real Supabase Auth |
| Realtime (dashboard) | — | ❌ not started, Phase 5 |
| Deployment | Vercel (frontend), TBD (backend — Railway mentioned in README) | ⚠️ backend host not finalized |

## 6. Twilio Integration Plan (Phase 3 target)

1. Twilio Voice webhook → FastAPI endpoint returns TwiML that opens a
   Media Stream to a new WebSocket route (reuse `routes/ws.py` pattern,
   don't fork it into a separate handler)
2. Incoming Twilio phone number maps to `tenant_id` via a new
   `tenant_phone_numbers` table (one distributor may eventually want more
   than one number, e.g. per region — model it as one-to-many from the
   start)
3. Everything downstream (STT → agent → TTS) reuses the existing
   `VoicePipeline` and `AgentRunner` — the only new code is the Twilio
   webhook handler and the PCM format adaptation (Twilio sends mulaw
   8kHz, current pipeline expects 16kHz PCM — needs a resampling step)
