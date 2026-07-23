# Day 2 — Async DB And Latency Theory

## Status

Complete. Theory studied, ready for implementation.

## Main learning goal

Understand why synchronous database calls inside async handlers are the biggest latency risk for a voice AI agent, and what caching patterns solve read-heavy hot paths.

The important senior AI engineering lesson:

> On a live phone call, every millisecond of silence is felt. You cannot fix voice latency by tuning the model — you fix it by not blocking the event loop.

## What I learned

### 1. The event loop problem

FastAPI uses Python's `asyncio` event loop. When you write:

```python
async def handle_turn(...):
    result = db.query(...)  # synchronous, blocks!
```

The `async def` doesn't make the function non-blocking — it only means you *can* use `await`. If the body contains a synchronous DB call, the entire event loop pauses for the duration of that network round-trip.

On a voice call, 2–3 tool calls per turn × 50–100ms DB latency each = 150–300ms of avoidable silence. That's the difference between a call that feels natural and one that feels broken.

### 2. The fix: async SQLAlchemy

SQLAlchemy 2.0 supports async engines via `asyncpg`:

```python
# Before (sync — blocks event loop)
engine = create_engine(DATABASE_URL)
session = sessionmaker(bind=engine)

# After (async — non-blocking)
engine = create_async_engine(DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"))
session = async_sessionmaker(bind=engine)

# Usage
async with session() as db:
    result = await db.execute(select(Stock).where(...))
```

Every tool function (`check_stock`, `lookup_supplier`, `create_po`, etc.) becomes an `async def` that `await`s its DB calls.

### 3. The ripple effect

Converting `db.py` to async means:
- All tool functions in `tools.py` become `async def`
- The dispatcher `execute_tool()` must `await` each tool
- `runner.py`'s tool-calling loop must `await execute_tool()`
- The `session_scope()` context manager becomes an async context manager

Files touched:
- `apps/api/voxflow_api/db.py`
- `apps/api/voxflow_api/agent/tools.py`
- `apps/api/voxflow_api/agent/runner.py`
- `requirements.txt` (add `asyncpg`)

### 4. Caching hot reads

`check_stock` and `lookup_supplier` are called on nearly every turn but read data that changes infrequently. Cache them:

- In-process TTL cache (`cachetools.TTLCache` or hand-rolled dict + timestamp)
- 30–60 second TTL — long enough to skip redundant DB hits, short enough to avoid stale data
- `create_po` and stock-mutating actions invalidate relevant cache entries

### 5. Supabase connection string nuance

Supabase provides two Postgres connection modes:

| Mode | Connection string | Use case |
|---|---|---|
| Session (direct) | `postgresql://...:6543/postgres` | Long-running backends — supports prepared statements |
| Transaction (pgbouncer) | `postgresql://...:6543/postgres?pgbouncer=true` | Serverless functions — connection pooling |

For a long-running FastAPI backend, use the **session (direct)** connection string on port 6543. The transaction-mode pooler breaks prepared statement caching and session state.

### 6. Latency budget for a voice call

| Step | Target latency | Notes |
|---|---|---|
| STT (faster-whisper) | 200–600ms | Runs in executor thread, already non-blocking |
| LLM (Groq) | 300–800ms per iteration | Multiple tool calls compound |
| DB round-trip | 0ms to cache, ~50ms to DB | **After async fix + caching** |
| TTS (edge-tts) | 200–500ms | Network call to Microsoft |

Total target per turn: ~1–2s. The fix for DB latency is the highest-impact change available.

## What was studied

| Topic | Source |
| --- | --- |
| ASGI vs WSGI, event loop mechanics | FastAPI docs, Python asyncio docs |
| SQLAlchemy 2.0 async engine | SQLAlchemy docs — `AsyncEngine`, `AsyncSession`, `async_sessionmaker` |
| asyncpg | asyncpg docs — pure-Python async Postgres driver |
| TTL caching patterns | `cachetools` docs, application-level vs distributed caching |
| Supabase connection pooling | Supabase docs — session vs transaction mode |
| Voice latency budgets | Twilio best practices, WebRTC latency guides |

## Key insight

The architecture choice mattering most right now is not which database or which LLM — it's whether the DB layer blocks the event loop. Every other optimization (better STT, faster LLM, CDN-hosting) is incremental. Fixing sync→async removes the single biggest latency multiplier.

## Interview explanation

In a voice AI system, the user feels every millisecond of delay as silence on the call. The biggest problem in the current codebase is that database calls are synchronous inside async handlers, blocking the event loop. I studied how SQLAlchemy's async engine works — using `create_async_engine` with `asyncpg` and `async_sessionmaker` — and how a simple TTL cache on hot-read functions like `check_stock` can eliminate redundant DB round-trips entirely.

## Non-technical explanation

When you call a number and the AI answers, every pause between what you say and what it says back feels like a broken connection. Right now, the system pauses because it's waiting for the database to respond — and while it waits, it can't do anything else. We're going to fix that by making database access non-blocking, so the AI can keep processing while it waits for data.

## Day 2 outcome

Solid theoretical foundation for the async DB migration and caching layer. Ready to implement.

## Next step after Day 2

Day 3 should study Twilio Media Streams, audio codec handling (mulaw→PCM resampling), and WebSocket audio architecture — the theory needed for Week 2 implementation.
