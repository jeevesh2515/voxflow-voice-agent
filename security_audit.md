# VoxFlow — Security Audit

**Date:** 2026-08-13  
**Auditor:** Senior AI Engineer (automated + manual review)  
**Status:** ✅ Production-ready for pilot

---

## 1. Authentication & Authorisation

| Control | Status | Notes |
|---|---|---|
| Staff dashboard auth | ✅ Real | Supabase Auth (`@supabase/ssr`) — email/password. JWT validated on every backend request. No `localStorage` bypass. |
| Backend JWT middleware | ✅ Active | `AuthMiddleware` in `auth.py` validates Supabase JWTs using JWKS. Rejects expired/invalid tokens with 401. |
| Twilio webhook signature | ✅ Enforced | `TWILIO_VALIDATE_SIGNATURE=true`. `RequestValidator` checks `X-Twilio-Signature` on every POST `/twilio/voice`. |
| Caller identity verification | ✅ Two-factor | Factor 1: inbound phone number matched against `tenant_phone_numbers`. Factor 2: city/GSTIN cross-check. `verify_caller` tool. |
| Tier 2 PIN for write actions | ✅ Active | `verify_pin` required before `create_po`. `pin_verified` flag on `CallSession`. Blocked and logged on failure. |
| Public `/api/active-calls` | ⚠️ Auth-aware | Returns only tenant-scoped data. Requires valid Supabase JWT in production (AuthMiddleware). Demo mode (no JWT) returns default tenant only. |

---

## 2. Database & Row-Level Security

| Control | Status | Notes |
|---|---|---|
| RLS enabled | ✅ Yes | Enabled on all 11 core tables in the production Supabase project. |
| Cross-tenant isolation | ✅ Verified | Deliberate cross-tenant query was blocked at RLS layer in Day 12 test. Application code defensively filters by `tenant_id` too. |
| Service role key scope | ✅ Backend only | `SUPABASE_SERVICE_ROLE_KEY` is only in `.env` (never shipped to frontend). Frontend uses `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` only. |
| SQLite dev database | ✅ No RLS risk | Dev uses SQLite (no network). Production switches to Supabase via `DATABASE_URL`. |

---

## 3. Rate Limiting

| Endpoint | Limit | Implementation |
|---|---|---|
| `POST /twilio/voice` | 30 requests/60s per IP | Sliding window, in-process dict. Returns HTTP 429. |
| `WS /twilio/media` | 10 connections/60s per IP | Sliding window, separate dict. Closes WS with code 1008. **Added Day 18.** |
| `GET /api/*` | None explicit | Protected by Supabase Auth JWT — requires valid session. |
| Browser WebSocket `/ws` | None explicit | Authenticated session required (Supabase JWT). |

---

## 4. Secret Management

| Secret | Location | Exposed in git? |
|---|---|---|
| `GROQ_API_KEY` | `.env` (gitignored) | ❌ Never |
| `TWILIO_ACCOUNT_SID` | `.env` (gitignored) | ❌ Never |
| `TWILIO_AUTH_TOKEN` | `.env` (gitignored) | ❌ Never |
| `TWILIO_API_KEY` / `TWILIO_API_SECRET` | `.env` (gitignored) | ❌ Never |
| `SUPABASE_SERVICE_ROLE_KEY` | `.env` (gitignored) | ❌ Never |
| `SUPABASE_URL` | `.env` + `.env.local` (gitignored) | ❌ Never in git |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | `.env.local` (gitignored) | ❌ Never in git |
| `DATABASE_URL` (Postgres with password) | `.env` (gitignored) | ❌ Never |
| Admin name/email/password | Not in any env file | N/A |

**`.gitignore` covers:** `.env`, `.env.local`, `.env.*.local`, `*.pem`, `*.key`  
**Verify with:** `git log --all --full-history -- .env` — no commits.

---

## 5. Network & TLS

| Control | Status | Notes |
|---|---|---|
| TLS on public endpoint | ✅ Let's Encrypt | Caddy handles HTTPS at `voxflow.duckdns.org`. Auto-renews. |
| HTTP→HTTPS redirect | ✅ Caddy default | Port 80 redirects to 443. |
| CORS | ✅ Restricted | `API_CORS_ORIGINS` env var. Default: `http://localhost:3000`. Production: Vercel domain only. |
| WebSocket over TLS | ✅ `wss://` | Twilio Media Streams connect over `wss://`. |

---

## 6. Input Validation

| Control | Status | Notes |
|---|---|---|
| Host header injection in TwiML | ✅ Sanitised | Regex `^[\w\.\-]+(:\d+)?$` validates `Host` before embedding in `<Stream url>`. |
| Twilio form fields | ✅ String cast | All form values cast to `str` before use. No SQL injection path (SQLAlchemy ORM with parameterised queries). |
| LLM-generated SQL | ✅ N/A | Agent uses ORM calls only, never raw SQL. No injection surface. |
| Caller-supplied phone number | ✅ Normalised | Stripped to digits only, length-checked (≥7 digits) before DB lookup. |

---

## 7. Security Headers

| Header | Applied to | Status |
|---|---|---|
| `X-Content-Type-Options: nosniff` | `POST /twilio/voice` TwiML response | ✅ Added Day 18 |
| `X-Frame-Options: DENY` | `POST /twilio/voice` TwiML response | ✅ Added Day 18 |
| `Cache-Control: no-store` | `POST /twilio/voice` TwiML response | ✅ Added Day 18 |
| Security headers on API | Vercel/Caddy level | ⚠️ Not yet added to FastAPI middleware |

---

## 8. Known Gaps (Explicitly Noted, Not Silently Assumed Fixed)

| Gap | Risk | Mitigation |
|---|---|---|
| No API-level rate limit on `/api/*` GET routes | Low — requires valid Supabase JWT | Acceptable for pilot (single-tenant, small team) |
| No security headers FastAPI middleware | Low — API responses are JSON/XML, not rendered HTML | Add `starlette.middleware.httpsredirect` + headers middleware post-pilot |
| VAD thresholds uncalibrated on real callers | Medium — could cause partial utterances | Tune Day 10 once backend back online |
| `ACME_EMAIL` in `.env` exposed to logs | Low — email only, not a credential | Non-sensitive; no action needed |
| Groq free tier (no SLA, rate-limited) | Medium — pilot outages possible | Upgrade to paid tier before production |

---

## 9. Verification Commands

```bash
# Confirm no secrets in git history
git log --all --full-history -- .env
git log --all --full-history -- .env.local

# Confirm .gitignore covers env files
grep -E "^\.env" .gitignore

# Run full test suite
python3 -m pytest apps/api/tests/ -q

# Build frontend (0 errors required)
cd apps/web && npm run build
```
