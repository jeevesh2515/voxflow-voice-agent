# Day 4 — Async DB Implementation (Week 1, Day 1)

## Status

**Planned.** Ready to implement. Theory covered in Day 2.

## Theory review

### The event loop problem

FastAPI uses asyncio. Every synchronous DB call in `tools.py` blocks the event loop for 50–100ms. Across 2–3 tool calls per turn, that's 150–300ms of silence on a live call. Users feel this as "the system is broken."

### The fix

Convert `db.py` from synchronous SQLAlchemy to async SQLAlchemy with `asyncpg`. Every tool function becomes an `async def` that `await`s its DB operations.

## Implementation checklist

### Step 1: Add asyncpg dependency

- [ ] Add `asyncpg` to `apps/api/requirements.txt`

### Step 2: Convert db.py

- [ ] Replace `create_engine` with `create_async_engine`
- [ ] Replace `sessionmaker` with `async_sessionmaker`
- [ ] Convert `session_scope()` from sync context manager to `async def` context manager using `async with`
- [ ] Use connection string with `postgresql+asyncpg://` prefix

### Step 3: Update tools.py

- [ ] Convert every tool function to `async def`
- [ ] Replace `db.execute(...)` with `await db.execute(...)`
- [ ] Replace `db.get(...)` with `await db.get(...)`
- [ ] Replace `db.commit()` with `await db.commit()`
- [ ] Update `execute_tool()` dispatcher to `await` each tool

### Step 4: Update runner.py

- [ ] Update tool-calling loop to `await execute_tool(...)`
- [ ] Ensure `handle_turn` properly awaits all async operations

### Step 5: Verify

- [ ] Run existing tests (`pytest apps/api/tests`)
- [ ] Confirm no synchronous DB calls remain in `tools.py` (grep for `def ` without `async def` + any `db.` calls)
- [ ] Run a manual test call through the browser simulator

### Step 6: Add caching layer (Day 2 stretch goal)

- [ ] Add `cachetools` to `requirements.txt`
- [ ] Create `voxflow_api/cache.py` with TTL cache
- [ ] Wrap `check_stock` reads with cache, keyed by `(tenant_id, sku, warehouse)`
- [ ] Wrap `lookup_supplier` reads with cache
- [ ] Invalidate cache on `create_po` and stock mutations

## Files to modify

| File | Change |
| --- | --- |
| `apps/api/requirements.txt` | Add `asyncpg` (and `cachetools` for Day 2) |
| `apps/api/voxflow_api/db.py` | Convert engine, session, session_scope to async |
| `apps/api/voxflow_api/agent/tools.py` | Convert every tool + dispatcher to async |
| `apps/api/voxflow_api/agent/runner.py` | Convert tool-calling loop to async |
| `apps/api/voxflow_api/voice/pipeline.py` | Check if any direct DB calls need async update |
| `apps/api/voxflow_api/routes/data.py` | Check REST endpoints for sync DB calls |
| `apps/api/voxflow_api/verify_db.py` | Check if verification script needs update |

## Expected validation

```
pytest apps/api/tests
# Expected: all tests passing (15/15)

# Confirm no sync DB calls remain:
grep -n "def " apps/api/voxflow_api/agent/tools.py | grep -v "async def"
# Expected: no output — every function should be async

# Verify async DB engine:
grep -n "create_async_engine" apps/api/voxflow_api/db.py
# Expected: exactly one match
```

## If something breaks

**Most likely failure:** tests that mock the session need update because the session is now an `AsyncSession` rather than a `Session`.

**Fix pattern for tests:**
```python
# Before
mock_session.query(Stock).filter(...).all()

# After (async session)
result = await mock_session.execute(select(Stock).where(...))
result.scalars().all()
```

**Second likely failure:** raw SQL or `text()` queries that worked with sync SQLAlchemy may need adjustment for async execution.

## Definition of done

1. All DB operations use async engines — no synchronous `session.query()` or `session.execute()` calls
2. Every tool function in `tools.py` is `async def` with `await` on DB calls
3. `execute_tool()` dispatcher awaits tool execution
4. Test suite passes cleanly
5. Manual browser simulator call completes successfully

## After implementation

Update `MEMORY.md`:
- Move "DB calls are synchronous inside async handlers" from incomplete to completed
- Add "Async DB layer" to "What's Actually Done"
- Update latency baseline section if possible

## Next after Day 4

Day 5 — Supabase connection hygiene (direct vs pooled connection string) and latency measurement baseline (Week 1 Days 3–4).
