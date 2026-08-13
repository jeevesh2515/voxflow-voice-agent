# VoxFlow — Week 4 Implementation Log (Days 16–20)

**Date:** 2026-08-13  
**Engineer:** Senior AI Engineer  
**Branch:** `main`

---

## Day 16 — Live In-Progress Call Status

### What Was Built

**Backend — `apps/api/voxflow_api/routes/data.py`**
- Added `GET /api/active-calls` endpoint
- Reads live `CallSession` objects from `pipeline._sessions` (in-memory, tenant-scoped)
- Returns per-session: `call_id`, `caller_phone`, `caller_name`, `company_name`, `intent`, `verified`, `pin_verified`, `outcome`, `turn_count`, `elapsed_sec`, `started_at`
- Calls disappear from this list as soon as `end_session()` is called and they are persisted to Postgres

**Frontend — `apps/web/src/lib/api.ts`**
- Added `api.activeCalls(tenant_id?)` method

**Frontend — `apps/web/src/app/dashboard/calls/page.tsx`**
- Added `useElapsed(startedAt)` hook — updates every 1s via `setInterval`
- Added `ActiveCallCard` component — pulsing green dot (Tailwind `animate-ping`), caller identity, intent, elapsed mm:ss timer, turn count, verification badge
- `CallsPage` now polls `/api/active-calls` every 5s via `useSWR({ refreshInterval: 5000 })`
- Active calls section renders only when `activeCalls.length > 0` (zero noise at rest)

### Definition of Done ✅
Active calls appear on the dashboard with live elapsed timer while in progress.

---

## Day 17 — Escalation Queue (Pre-existing, Verified)

The escalation queue was already built during Week 3 as part of the calls dashboard work. Verification:

- `/dashboard/escalations` page: `EscalationCard` component, pending count, resolved dimming
- `PATCH /api/calls/{id}/resolution` endpoint: saves `staff_resolution` + `staff_resolved_at` timestamp
- API client: `api.patchResolution(call_id, staff_resolution)` in `api.ts`
- Escalated calls appear in `/dashboard/escalations` page filtered by `escalated OR follow_up_required`

### Definition of Done ✅
Escalated calls are visually distinct, can be marked resolved. Persists to Postgres.

---

## Day 18 — Security Pass

### Twilio API Key Support

**Files:** `config.py`, `.env.example`, `map_phone.py`

Two Twilio credential modes are now supported:

| Mode | When to Use | Env Vars |
|---|---|---|
| Account SID + Auth Token | **Always required** for webhook signature validation | `TWILIO_ACCOUNT_SID` + `TWILIO_AUTH_TOKEN` |
| API Key + API Secret | Optional — safer for CLI tools, rotation | `TWILIO_API_KEY` + `TWILIO_API_SECRET` |

`map_phone.py` uses the `_twilio_client()` helper which prefers API Key auth when both `TWILIO_API_KEY` and `TWILIO_API_SECRET` are set.

**To add your new Twilio API Keys:** Open `.env` and add:
```
TWILIO_API_KEY=SKxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_API_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```
These are used by CLI tools only. The webhook (`/twilio/voice`) always uses `TWILIO_AUTH_TOKEN` for signature validation — that cannot change.

### Rate Limiting — WebSocket Endpoint

**File:** `apps/api/voxflow_api/routes/twilio.py`

- `WS /twilio/media`: added `_ws_rate_limited()` — 10 connections per 60s per IP
- On rate limit: WebSocket accepted then immediately closed with code `1008` (policy violation)
- Separate bucket dict from the HTTP rate limiter (`_ws_rate_buckets`)
- `POST /twilio/voice`: existing 30 req/60s rate limit confirmed in place

### Security Headers on TwiML Response

**File:** `apps/api/voxflow_api/routes/twilio.py`

Added to `POST /twilio/voice` response:
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Cache-Control: no-store, no-cache
```

### security_audit.md

Created `security_audit.md` covering:
- Authentication & authorisation (Supabase Auth, JWT middleware, Twilio signature, caller 2FA, Tier 2 PIN)
- Database RLS (all 11 tables, cross-tenant isolation verified)
- Rate limiting (both endpoints documented)
- Secret management (no secrets in git — verified)
- Network & TLS (Caddy + Let's Encrypt)
- Input validation (host header injection, SQL injection path)
- Security headers
- Known gaps (explicitly noted, not silently assumed fixed)

### Verification

```
✅ python3 -m pytest apps/api/tests/ -q  →  136 passed in 6.85s
✅ cd apps/web && npm run build          →  16/16 routes compiled, 0 errors
✅ git log --all --full-history -- .env  →  no commits containing .env
```

---

## Days 19–20 — Pilot Prep (Pending)

**Day 19:** Demo call with Varun Beverages contact (or equivalent). Update `PRD.md` section 5 with real workflow findings. Identify single highest-value fix.

**Day 20:** Implement Day 19 finding. Final read-through of all docs. Pilot-readiness sign-off.

---

## Files Changed This Session

| File | Change |
|---|---|
| `apps/api/voxflow_api/config.py` | + `twilio_api_key`, `twilio_api_secret` fields |
| `.env.example` | + `TWILIO_API_KEY`, `TWILIO_API_SECRET` entries with docs |
| `apps/api/voxflow_api/map_phone.py` | + `_twilio_client()` helper preferring API Key auth |
| `apps/api/voxflow_api/routes/data.py` | + `GET /api/active-calls` endpoint |
| `apps/web/src/lib/api.ts` | + `api.activeCalls()` method |
| `apps/web/src/app/dashboard/calls/page.tsx` | + `ActiveCallCard`, `useElapsed`, live polling section |
| `apps/api/voxflow_api/routes/twilio.py` | + `_WS_RATE_LIMIT_MAX`, `_ws_rate_limited()`, security headers, WS rate limit |
| `security_audit.md` | New — comprehensive security state document |
| `PHASES.md` | Days 16–18 marked complete |
| `MEMORY.md` | Current position updated to Week 4 Day 18 |
