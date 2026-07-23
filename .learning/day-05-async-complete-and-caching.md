# Day 5 — Async DB Complete & Caching Layer (Week 1, Days 1–2)

## Status

**Completed.** All DB operations now use async engines. Cache layer added for hot reads. Security audit applied (live keys removed). All 15 tests passing.

## What was done

### Day 1 — Async database layer

- **`db.py`** — Added `create_async_engine` (auto-detects `sqlite+aiosqlite` for dev, `postgresql+asyncpg` for prod). Added `async_session_scope()` async context manager alongside the existing sync `session_scope()`.
- **`tools.py`** — All 12 tool functions + dispatcher converted to `async def` with `await db.execute(...)` / `await db.get(...)`.
- **`runner.py`** — `execute_tool()` call now awaited.
- **`pipeline.py`** — `_persist()` converted to async, uses `async_session_scope()`.
- **`routes/ws.py`** — `end_session()` calls now awaited.
- **`main.py`** — `pipeline._persist()` call now awaited.
- **Tests** — 4 tool tests converted to `@pytest.mark.asyncio` with `await execute_tool(...)`.

### Day 2 — Caching layer

- **`cache.py`** — Created `TTLCache` class with `get`, `set`, `invalidate`, `clear`, 30-second default TTL.
- **`tools.py`** — `check_stock` reads cached by `(tenant_id, sku, warehouse)`. `lookup_supplier` reads cached by `(tenant_id, phone, name)`. `create_po` clears stock cache on mutation.

### Day 5 — Fixes & security pass

- Removed all live API keys from `.env` and `apps/web/.env.local`.
- Fixed `voice/__init__.py` and module imports to avoid eager loading of heavy deps (faster-whisper, edge-tts) during test collection.
- Removed broken `@supabase/server` dependency from web `package.json`.
- Fixed root `.gitignore` — no longer excludes `voxflow-voice-agent/` directory.
- Updated `.env.example` files with clean placeholder values.

## What remains for Week 1

- [ ] **Day 3** — Supabase connection hygiene (direct vs pooled connection string)
- [ ] **Day 4 (complete)** — Latency measurement baseline (timing logs, baseline numbers in MEMORY.md)
- [x] **Day 5** — Buffer day / catch-up (used for Day 1–2 completion + security pass)

## Next

Week 2 — Real telephony (Twilio). Start with Day 6: Twilio account + webhook skeleton. See `PHASES.md` for details.
