# VoxFlow Setup and Deployment Guide

**Last updated:** 2026-08-26
**Current deployment:** FastAPI API on the Render Free Web Service and Next.js dashboard on Vercel. Vercel Production REST and WebSocket origins both target Render. Render is request-driven and may take about a minute to wake after idle time; this posture is for safe demonstrations, not a continuous telephony SLA.
**Campaign and side-effect safety:** `DURABLE_CAMPAIGN_WORKER_ENABLED=false` and `DURABLE_SIDE_EFFECTS_WORKER_ENABLED=false` must remain set in production unless a separately approved controlled pilot is being operated.

## 1. Deployment topology

```mermaid
flowchart LR
    U[Operators] --> W[Next.js dashboard\nVercel]
    W --> A[FastAPI API\nRender Free Web Service]
    T[Twilio inbound media streams] --> A
    A --> P[(PostgreSQL / Supabase-compatible DB)]
    A --> J[Durable job/outbox/event tables]
    J --> CW[Campaign worker\ncurrently disabled]
    J --> SW[Side-effect worker\ncurrently disabled]
    PC[Provider callback ingress\nsecret intentionally unset] --> A

```

| Component | Production URL | Role |
|---|---|---|
| Web dashboard | <https://voxflow-voice-agent.vercel.app> | Next.js operator UI. |
| API | <https://voxflow-voice-agent.onrender.com> | Request-driven FastAPI control plane, browser simulator, inbound voice, and jobs read models. |
| API health | <https://voxflow-voice-agent.onrender.com/api/health> | General API availability and free-service warm-up target. |
| Job health | <https://voxflow-voice-agent.onrender.com/api/jobs/health?tenant_id=varun> | Staged rollout/job visibility verification. |
| WebSocket | <wss://voxflow-voice-agent.onrender.com/ws/call> | Browser-only simulator transport; no outbound call is initiated by this endpoint. |

## 2. Local development

### Prerequisites

- Node.js 22 or later
- Python 3.12
- npm or pnpm
- SQLite for default local tests; a PostgreSQL-compatible database only when exercising production migration paths

### API

```bash
cd apps/api
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m voxflow_api.seed --reset
uvicorn voxflow_api.main:app --reload --port 8000
```

### Web dashboard

```bash
cd apps/web
npm install
cp .env.example .env.local
npm run dev
```

Set `NEXT_PUBLIC_API_URL=http://localhost:8000` in the web environment for local API calls. The dashboard is available at `http://localhost:3000`.

## 3. Database migrations

SQLite tests initialize from SQLAlchemy metadata. Production database upgrades use the repository’s ordered migration files. The durable campaign migration sequence is:

```text
migrations/003_durable_job_ledger.sql
migrations/004_outbox_relay_state.sql
migrations/005_campaign_policy_controls.sql
migrations/006_provider_callback_lifecycle.sql
migrations/007_dial_sandbox_callback_adapter.sql
migrations/008_typed_durable_side_effect_jobs.sql
migrations/009_controlled_pilot_readiness.sql
migrations/010_pilot_operations_evidence.sql
migrations/011_reliability_slos_drills.sql
migrations/012_tenant_memberships.sql
migrations/013_privacy_lifecycle_controls.sql
migrations/014_telephony_provider.sql
migrations/015_call_latency.sql
migrations/016_telephony_routing_and_caller_pins.sql
migrations/017_product_tenant_composite_key.sql
```

Run migrations through an approved PostgreSQL migration procedure. Migration `016` backfills route `updated_at`, adds exact route policy fields and PIN verifier timestamps, and migration `017` upgrades the product catalog to a composite primary key `(sku, tenant_id)`. Do not run a campaign worker merely to validate migration success. Use API health, test suites, and safe job-health reads instead.

## 4. Backend deployment and free-tier operation

Render is the active backend runtime because the API hosts HTTP routes, WebSocket/inbound voice behavior, and future separately deployed workers. The existing `render.yaml` declares a `plan: free` Docker web service and preserves the project’s fail-closed settings. Its request-driven Free Web Service sleeps after idle time. In the Vercel Phone Simulator, select **Prepare Simulator** before a browser-only session: it calls only the read-only `/api/health` endpoint, shows readiness and elapsed warm-up time, then enables the microphone and text controls. The retained [`fly.toml`](fly.toml) is a rollback/reference artifact only; it must not be deployed with a paid or always-on setting. Configure provider secrets only in the active provider’s secret manager; never commit production values.

| Environment variable | Purpose | Production guidance |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | Use a managed production database secret. |
| `DB_SCHEMA_BOOTSTRAP_MODE` | Startup schema policy: `auto`, `always`, or `skip` | **Use `auto` in Render production.** SQLite self-initializes; PostgreSQL verifies reviewed migration tables without repeating normal-boot DDL. |
| `API_CORS_ORIGINS` | Allowed browser origins | Include the Vercel production origin. |
| `PUBLIC_BASE_URL` | Public API base URL used by telephony/webhook paths | Use the Render API base URL or approved public ingress. |
| Telephony/LLM credentials | Provider integrations | Store only in Render secrets; never commit them. |
| `DURABLE_CAMPAIGN_WORKER_ENABLED` | Global campaign worker kill switch | **Keep `false` in production.** |
| `DURABLE_CAMPAIGN_CANARY_TENANTS` | Future canary admission list | Keep empty until explicit approval. |
| `DURABLE_CAMPAIGN_DRY_RUN` | Provider-free campaign-worker path | Keep enabled for staging/dry-run evidence. |
| `PROVIDER_CALLBACK_VALIDATE_SIGNATURE` | Enables HMAC/timestamp verification for normalized callbacks | **Keep `true`.** |
| `PROVIDER_CALLBACK_SHARED_SECRET` | Callback ingress HMAC secret | **Leave unset until a provider-specific Day 33 sandbox adapter is approved.** An unset secret fails closed. |
| `PROVIDER_CALLBACK_MAX_AGE_SECONDS` | Maximum signed callback age | Retain the default `300` unless an approved provider contract requires another bounded value. |
| `DIAL_CALLBACK_ADAPTER_ENABLED` | Day 33 Dial-specific ingress switch | **Keep `false` in production.** It returns 503 before body parsing or persistence. |
| `DIAL_CALLBACK_SANDBOX_MODE` | Prevents non-sandbox adapter operation | **Keep `true`.** The endpoint requires this value even when deliberately enabled for fixtures. |
| `DIAL_CALLBACK_ALLOWED_TENANTS` | Stored-operation tenant application allow-list | Keep empty. A verified adapter event cannot apply without a deliberate sandbox tenant admission. |
| `DIAL_CALLBACK_SIGNING_SECRETS` | Current/previous Dial webhook HMAC secret overlap | **Leave unset.** Never place secrets in logs, documents, browser configuration, or version control. |
| `DIAL_CALLBACK_MAX_AGE_SECONDS` | Dial webhook replay-age bound | Retain `300` unless a reviewed provider contract requires another bounded value. |
| `DURABLE_SIDE_EFFECTS_WORKER_ENABLED` | Independent operational side-effect worker hard stop | **Keep `false` in production.** The API must never claim Sheets/email/CRM/notification/recording jobs. |
| `DURABLE_SIDE_EFFECTS_DRY_RUN` | Provider/integration-free side-effect worker path | **Keep `true`** until a tenant-specific approval and dry-run evidence exist. |
| `DURABLE_SIDE_EFFECTS_ALLOWED_TENANTS` | Future side-effect worker admission list | Keep empty. A worker cannot build without an explicit tenant. |
| `DURABLE_SIDE_EFFECTS_MAX_CONCURRENCY` | Maximum concurrent operational side effects per worker | Retain `1` for staged/dry-run validation. |
| `PILOT_READINESS_ENFORCED` | Day 35 approval gate | **Keep `true`** with an empty approved-tenant list until human authorization is released. |
| `PILOT_OPERATIONS_EVIDENCE_ENFORCED` | Day 36 fresh same-cohort hold-point gate | **Keep `true`.** Missing, stale, paused, blocked, rollback-requested, or version-mismatched evidence must remain fail closed. |

After deployment, verify only safe endpoints. Set `API_ORIGIN` to the active Render runtime.

```bash
API_ORIGIN=https://voxflow-voice-agent.onrender.com
curl -fsS "$API_ORIGIN/api/health"
curl -fsS "$API_ORIGIN/api/jobs/health?tenant_id=varun"
curl -fsS "$API_ORIGIN/api/campaign-policies/varun"
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$API_ORIGIN/api/provider-callbacks/events" -H 'Content-Type: application/json' -d '{}'
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$API_ORIGIN/api/provider-callbacks/dial/events" -H 'Content-Type: application/json' -d '{}'
curl -fsS "$API_ORIGIN/api/analytics/overview?tenant_id=varun&days=7"
curl -fsS "$API_ORIGIN/api/pilot-readiness/varun"
curl -fsS "$API_ORIGIN/api/pilot-readiness/varun/rollback-preview"
curl -fsS "$API_ORIGIN/api/pilot-operations/varun/preflight"
curl -fsS "$API_ORIGIN/api/pilot-operations/varun/hold-point"
# Confirm durable_side_effects is staged/dry-run/tenant-blocked with no intents/errors;
# pilot readiness and Day 36 preflight/hold-point are blocked without configuration;
# both callback requests return 503.
```

The health response also reports `db_schema_bootstrap_mode: "auto"` on the active Render deployment. Its startup log should report `db.schema_verified dialect=postgresql`; this is a read-only migration check, not table creation or compatibility DDL.

Expected Day 36 posture is `activation_mode: "staged"`, `canary_allowed: false`, campaign dry-run true, an unconfigured tenant policy, generic normalized callback ingress returning `503`, and Dial ingress returning `503 dial_callback_adapter_disabled` before body parsing. The analytics response must include `dial_sandbox_adapter` and `durable_side_effects`; the latter must show `activation_mode="staged"`, `dry_run=true`, `tenant_allowed=false`, and zero unplanned intent/error counts in an untouched deployment. Day 36 preflight and hold-point responses must be **blocked** for a tenant without configuration, show `no_auto_expansion=true`, `expansion_permitted=false`, and perform no mutation. These checks are intentionally malformed/read-only; they must never be replaced with a live Dial callback, configured secret, provider ping, Sheets write, Gmail fetch, CRM post, notification, recording retrieval, or side-effect-worker enablement during deployment verification.

### Tenant telephony configuration

After migration and API deployment, an authenticated tenant owner configures inbound lines from `/dashboard/settings`. Use E.164 numbers only. The destination number is immutable after creation; add a new line and deactivate the old one to change DID ownership. Unknown, inactive, or wrong-provider DIDs must return `404 unknown_connect_did` rather than falling back to a default tenant.

Caller PINs are set/reset per contact in the same owner-only settings page. Use 4–8 digits and confirmation. The browser never receives the stored verifier, and production onboarding/import paths do not assign a predictable default PIN when none is supplied. Operators, viewers, and demo sessions may inspect masked posture only. A contact locks for 15 minutes after 10 failed PIN attempts persisted across calls (not just within one call); an owner can immediately clear a lockout by setting a new PIN.

## 5. Vercel frontend deployment

Deploy `apps/web` as the Next.js project root. The current Production frontend uses the reviewed Render Free endpoints; Development and Preview remain independently configured.

| Variable | Current Production value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://voxflow-voice-agent.onrender.com` |
| `NEXT_PUBLIC_WS_URL` | `wss://voxflow-voice-agent.onrender.com` |
| Supabase public settings | Use approved public client values only; never a service-role key |

After Vercel reports success, verify the public and protected routes without invoking campaign actions:

```bash
curl -I https://voxflow-voice-agent.vercel.app/
curl -I https://voxflow-voice-agent.vercel.app/about
curl -I https://voxflow-voice-agent.vercel.app/pricing
curl -I https://voxflow-voice-agent.vercel.app/dashboard/campaigns
curl -I https://voxflow-voice-agent.vercel.app/dashboard/analytics
```

Public routes should return `200`. A session-free dashboard request should redirect to `/sign-in`. In an authenticated browser, verify the campaign page renders **Safe Staging** and **No Inline Dialling**, then verify the analytics page renders the read-only **Provider Lifecycle**, **Dial Sandbox Adapter**, **Durable Side Effects**, **Controlled Pilot Readiness**, and **Pilot Operations Evidence** panels. In the safe default deployment the adapter panel must display **STAGED**, **BLOCKED**, and zero audit/failure totals; the Day 34 panel must show **STAGED**, zero intents/errors, tenant **BLOCKED**, and dry-run protection; Day 35 must show **BLOCKED**, cohort `0/0`, zero rollback actions, and `Pilot Configuration Missing`; Day 36 must show **BLOCKED**, zero running/callback flags, and **NO AUTO-EXPANSION · HUMAN HOLD POINT REQUIRED**. No panel can expose a provider/integration configuration or trigger an action.

## 6. Free-tier demonstration workflow and Fly standby

Before a demonstration, warm Render with `curl -fsS https://voxflow-voice-agent.onrender.com/api/health`, then promptly open the Vercel Phone Simulator and use a text-only quick prompt. Both Vercel production origins must remain on Render; update `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_WS_URL` together and redeploy Vercel after any backend-origin change. Keep Fly stopped unless an owner explicitly approves a separate rollback; never transfer a provider secret, worker allow-list, or activation setting as part of a provider change.

## 7. Quality gate before a delivery

```bash
# Backend
cd apps/api
.venv/bin/ruff check voxflow_api tests
.venv/bin/pytest -q

# Frontend, from repository root
npm run lint --workspace=apps/web
npm run build --workspace=apps/web
```

A delivery is not complete until the relevant GitHub CI workflow succeeds and the Vercel deployment status for the same commit succeeds.

## 8. Campaign and side-effect worker operating rule

Workers are intentionally separated from the API request path. Neither worker may be started manually on a developer machine against production credentials, and neither may be enabled merely because the dashboard exposes a campaign or side-effect read model. FastAPI must not start the legacy Sheets retry or email scan loops.

Before a future internal canary, confirm all of the following:

1. The global worker switch is intentionally changed through an approved release.
2. Exactly one internal tenant is in the allow-list.
3. The tenant policy is valid and enabled.
4. The E.164 test target has consent and no opt-out.
5. Daily limit and in-flight capacity are one.
6. Provider sandbox or dry-run has passed, including signed callback duplicate/reorder/unknown-call drills.
7. An operator can monitor jobs, policy decisions, provider operations, and rollback.

Before a controlled pilot, apply the same rule to operational side effects: a worker must have a written tenant approval, an explicit tenant allow-list, dry-run evidence, a named operator, integration-specific credential review, and rollback ownership. Day 35 adds the final one-tenant/fixed-cohort/operating-hours/human-escalation/scorecard gate; Day 36 additionally requires a fresh current-version same-cohort preflight/hold-point record. Readiness and evidence are not activation or automatic expansion.

## 9. Cloud-native distribution — one-line clone (Day 54)

Every runtime is hosted and free. No local model, no GPU, no Docker needed to contribute.

```bash
git clone https://github.com/jeevesh2515/voxflow-voice-agent.git
cd voxflow-voice-agent
cp .env.example .env          # fill only GROQ_API_KEY + Supabase pooler URL
cd apps/web && npm install && npm run dev   # http://localhost:3000
# in another terminal:
cd apps/api && python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && python -m voxflow_api.seed --reset
uvicorn voxflow_api.main:app --reload --port 8000
# live demo: vercel --prod  (reads NEXT_PUBLIC_API_URL from Vercel env)
```

**Free-tier stack:** Groq `whisper-large-v3-turbo` (STT) + `llama-3.1-8b-instant`/`openai/gpt-oss-20b` (LLM) + `edge-tts` (browser TTS, no key) + Supabase Free pooler (`aws-*.pooler.supabase.com:5432`) + Render Free + Vercel Hobby. No `requirements-local.txt`.

**Cold start:** Render Free sleeps. Keep it warm with `scripts/supabase_keepalive.py` (cron) and a Vercel cron hitting `GET /api/health` every 14 min. `BENCHMARK_REPORT.md` notes cold vs warm — a cold P50 is a wake-up, not a voice latency.

**Day 54 perf:** Dynamic tool gating (core 6 tools pre-verify, ~1.5k tokens saved), parallel reads via `asyncio.gather`, and streaming `turn_start` + `audio_chunk` over `/ws/call` (first byte ~150ms TTFB, not 300ms buffered). `GROQ_FALLBACK_MODEL=llama-3.1-8b-instant` keeps the free tier fast when the primary is rate-limited.

## 10. Historical self-hosted instructions

Older Oracle Cloud, DuckDNS, Caddy, and Docker-compose notes were superseded by the current Render/Vercel deployment path. Keep any environment-specific runbook outside this document and label it with its runtime/date; do not present it as the production default.

## References

- [README](README.md)
- [Architecture](ARCHITECTURE.md)
- [Security audit](security_audit.md)
- [Current phase plan](PHASES.md)
- [Render configuration](render.yaml)
- [Vercel configuration](vercel.json)
