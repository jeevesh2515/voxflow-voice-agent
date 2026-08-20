# VoxFlow

VoxFlow is a **Hindi-English voice operations platform** for supply-chain teams. It combines a FastAPI voice and operations backend with a Next.js dashboard for inbound support workflows, operational data, campaigns, escalations, and durable dispatch visibility.

> **Current production posture:** campaign dispatch and operational side-effect workers are independently disabled. Day 35 pilot admission is additionally **fail-closed** with an empty tenant allow-list. No API request, browser verification, or dashboard action should place a real provider call, send a notification, post a CRM webhook, write Sheets, fetch Gmail, or retrieve a recording unless a separately approved future pilot enables the correct worker and tenant controls.

| Area | Current implementation |
|---|---|
| Frontend | Next.js **16.3.1**, TypeScript, Tailwind CSS, SWR, deployed on Vercel. |
| Backend | FastAPI, Python 3.12, SQLAlchemy 2.0, SQLite for local tests and PostgreSQL-compatible production migrations. |
| Voice | Twilio inbound webhook/media-stream path, Dial provider adapter for outbound capability, Hindi-English agent tooling. |
| Durable execution | PostgreSQL-backed job ledger, transactional outbox, atomic claims, leases, retry/backoff, graceful drain, provider-operation idempotency, and redacted typed side-effect intents. |
| Campaign safety | Feature gate, canary scoping, dry-run mode, tenant policy checks, consent/opt-out controls, capacity reservations, audit decisions, cancellation, and Day 35 fail-closed pilot cohort admission. |
| Analytics and reporting | Tenant-safe KPI/trend aggregates, durable monitoring signals, provider-lifecycle totals, operator attention queue, and redacted CSV enterprise reports. |
| Provider callbacks | Fail-closed normalized ingress plus a Dial-specific sandbox adapter: official-envelope HMAC verification, signed fixture normalization, redacted audit receipts, tenant rollout gate, immutable lifecycle reconciliation, and quarantine. |
| Production | [Vercel dashboard](https://voxflow-voice-agent.vercel.app) and [Render API](https://voxflow-voice-agent.onrender.com/api/health). |

## What is complete through Day 35

VoxFlow has completed the durable-campaign foundation and policy-control program. Campaign targets are queued as durable jobs rather than called from the HTTP request path. The worker implementation protects provider side effects with a tenant-scoped idempotency key and reconciles provider terminal results without a blind re-dial.

Day 30 adds an explicit permission boundary before a provider operation may be reserved. The handler requires an enabled tenant policy, an active campaign, recorded recipient consent, no opt-out, an allowed consent purpose, an open tenant-local calling window, daily budget, and available tenant capacity. A denied target is terminally **cancelled** with immutable audit evidence. A temporarily ineligible target is **deferred** to the exact next eligible time.

Day 31 turns persisted calls, campaign targets, policy decisions, jobs, leases, and outbox state into a tenant-safe analytics read model. The dashboard presents real KPIs, daily trends, durable-work attention signals, staged rollout status, and a CSV report that excludes transcripts, phone numbers, raw job payloads, and policy evidence.

Day 32 adds the provider-to-VoxFlow lifecycle return path. `POST /api/provider-callbacks/events` is fail-closed when its signature secret is absent, derives tenant ownership only from a stored provider operation, records each verified event immutably, quarantines unknown provider IDs, and prevents duplicate or late events from reopening terminal work or causing a re-dial. Provider lifecycle totals are visible as aggregates only in the analytics dashboard and enterprise CSV.

Day 33 isolates Dial’s documented webhook protocol at the integration edge. `POST /api/provider-callbacks/dial/events` remains disabled unless sandbox mode, a signing secret, and an explicit tenant allow-list are configured. It verifies `X-Dial-Signature` over the raw body, supports an intentional current/previous-secret overlap, normalizes only outbound Dial call events, acknowledges a signed `webhook.ping` without business mutation, writes redacted adapter audit receipts, and hands eligible lifecycle observations to the Day 32 service. It never registers a provider subscription, fetches a provider secret, or initiates a call.

Day 34 removes API-process ownership of operational side effects. Sheets mirrors, email scans, CRM webhooks, notifications, generic worksheet writes, and recording follow-up now persist a tenant-scoped `SideEffectIntent`, `JobRun`, and `JobOutbox` atomically. A separately deployed side-effect worker is disabled by default, requires an explicit tenant allow-list, and records a dry-run result instead of external IO. The dashboard exposes aggregate-only durable side-effect health; direct agent Twilio/Dial calls and fire-and-forget CRM dispatch are blocked.

Day 35 adds a controlled-pilot readiness contract without an activation control. An eligible future target must pass the ordinary tenant policy and a second independent gate: an environment-approved tenant, an approved/unexpired pilot configuration, a reviewed hashed cohort, named primary and backup escalation owners, micro-cohort capacity, and a frozen metric-contract version. The read-only scorecard reports the exact completion, escalation, FCR, and confirmed-security-incident definitions; the database-only rollback drill cannot run while the worker is active or a pilot claim is live. The real pilot remains intentionally blocked until a human-owned one-tenant operating package is signed.

| Day | Delivered capability | Primary evidence |
|---:|---|---|
| 25 | Durable job ledger, outbox, attempts, and provider operations | Migration `003_durable_job_ledger.sql` |
| 26 | Atomic claims, leases, stale-worker protection, and recovery | Lease and competing-worker tests |
| 27 | Generic worker runtime, full-jitter retries, and graceful drain | Worker runtime tests |
| 28 | Transactional outbox relay, job-health APIs, operator panel, safe staging | Migration `004_outbox_relay_state.sql` |
| 29 | Controlled canary worker, dry run, no-redial provider reconciliation | Campaign-dispatch integration tests |
| 30 | Tenant policy, consent, opt-out, budget/capacity controls, auditable cancellation | Migration `005_campaign_policy_controls.sql` |
| 31 | Advanced analytics, pull-based monitoring, operator attention queue, redacted enterprise CSV reporting | `tests/test_analytics.py` and `/api/analytics` |
| 32 | Signed callback ingress, immutable provider events, quarantine, idempotent terminal reconciliation, lifecycle analytics | `tests/test_provider_callbacks.py` and migration `006_provider_callback_lifecycle.sql` |
| 33 | Dial sandbox adapter, raw-body HMAC verification, secret-rotation overlap, outbound-event normalization, redacted audit ledger, tenant rollout gate, and analytics visibility | `tests/test_dial_callback_adapter.py`, `tests/test_analytics.py`, and migration `007_dial_sandbox_callback_adapter.sql` |
| 34 | Typed side-effect intents/jobs for Sheets, email scans, CRM sync, notifications, worksheet writes, and recording retrieval; separate gated worker; no direct dispatch; analytics/operator panel | `tests/test_side_effect_jobs.py`, `tests/test_analytics.py`, and migration `008_typed_durable_side_effect_jobs.sql` |
| 35 | Fail-closed pilot admission, hashed fixed cohort, expiry/capacity/escalation contract, frozen scorecard, read-only readiness APIs, dashboard evidence panel, and database-only rollback drill | `tests/test_pilot_readiness.py`, migration `009_controlled_pilot_readiness.sql`, and `railway.json` |

## Production safety controls

The following controls are intentional and must remain in place until a formal pilot canary is approved.

| Control | Meaning |
|---|---|
| `DURABLE_CAMPAIGN_WORKER_ENABLED=false` | Global hard stop for campaign worker execution in production. |
| `activation_mode: staged` | Job-health endpoint communicates that dispatch is not active. |
| `canary_allowed: false` | The deployed tenant is not admitted to a canary worker cohort. |
| `dry_run: true` | The deployed read model reports a non-provider test posture. |
| Unconfigured tenant policy | A future worker attempt fails closed rather than assuming call permission. |
| `DIAL_CALLBACK_ADAPTER_ENABLED=false` | Dial provider-specific ingress rejects before body parsing or persistence. |
| `DIAL_CALLBACK_SANDBOX_MODE=true` | The adapter is certification-only and cannot imply a production provider rollout. |
| Empty `DIAL_CALLBACK_ALLOWED_TENANTS` / `DIAL_CALLBACK_SIGNING_SECRETS` | No normalized Dial event is eligible for application; an enabled adapter still fails closed without a secret. |
| `DURABLE_SIDE_EFFECTS_WORKER_ENABLED=false` | Independent hard stop for Sheets, email, CRM, notification, and recording job execution. |
| `DURABLE_SIDE_EFFECTS_DRY_RUN=true` | A future admitted side-effect worker records dry-run evidence rather than external integration IO. |
| Empty `DURABLE_SIDE_EFFECTS_ALLOWED_TENANTS` | No tenant is eligible for operational-side-effect worker claims. |
| `PILOT_READINESS_ENFORCED=true` plus empty `PILOT_READINESS_APPROVED_TENANTS` | The Day 35 target-admission gate denies every tenant until a written pilot approval is independently reflected in a future environment change. |

An approved live canary needs all of the following: one explicitly allowed tenant, a tenant policy with a valid IANA timezone and local calling window, a recorded consented E.164 test recipient, no opt-out, capacity and daily limit of one, dry-run evidence, an operator owner, and a rollback plan.

## Architecture

```mermaid
flowchart LR
    UI[Next.js dashboard\nVercel] --> API[FastAPI control plane\nRender]
    API --> DB[(PostgreSQL / SQLite)]
    API --> OB[Transactional outbox]
    OB --> JR[Durable job ledger]
    JR --> W[WorkerRuntime\nfeature-gated]
    W --> P{Tenant policy\nconsent, time, budget, capacity}
    P -- deferred/cancelled --> A[Audit decision + durable state]
    P -- allowed --> PO[ProviderOperation\nidempotency boundary]
    PO -->     D[Dial outbound client]
    D --> C[Dial sandbox adapter\nHMAC + normalizer + tenant gate]

    C --> E[Immutable ProviderEvent ledger]
    E --> R[Idempotent reconciliation + quarantine]
    R --> DB
    API --> T[Twilio inbound media streams]
    DB --> AN[Analytics and report read model]
    AN --> UI
```

The HTTP API persists intent quickly. A durable worker—not an HTTP handler—owns campaign execution. The policy evaluator runs before provider intent reservation, and provider callbacks/reconciliation update the same durable operation rather than creating a second call.

## Repository layout

```text
apps/
  api/                         FastAPI service, durable jobs, migrations tests
  web/                         Next.js dashboard
migrations/                    Production PostgreSQL migration scripts
.learning/                     Local-only daily implementation and theory journal
.planning/                     Planning archive and current roadmap index
docs/                          Product architecture and demo material
```

## Local development

### Prerequisites

- Node.js 22 or newer
- Python 3.12
- npm or pnpm

### Start the API

```bash
cd apps/api
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m voxflow_api.seed --reset
uvicorn voxflow_api.main:app --reload --port 8000
```

### Start the dashboard

```bash
cd apps/web
npm install
cp .env.example .env.local
npm run dev
```

The dashboard runs at `http://localhost:3000`; the API runs at `http://localhost:8000`.

### Local database and migrations

SQLite test and development databases are created from SQLAlchemy metadata. Production PostgreSQL must apply the checked-in migration sequence in order:

```text
migrations/003_durable_job_ledger.sql
migrations/004_outbox_relay_state.sql
migrations/005_campaign_policy_controls.sql
migrations/006_provider_callback_lifecycle.sql
migrations/007_dial_sandbox_callback_adapter.sql
migrations/008_typed_durable_side_effect_jobs.sql
migrations/009_controlled_pilot_readiness.sql
```

Do not enable the campaign worker as a migration smoke test. The policy and worker test suites use mocked providers and must remain the default verification path.

## Quality checks

Run all backend checks from `apps/api`:

```bash
.venv/bin/ruff check voxflow_api tests
.venv/bin/pytest -q
```

Run frontend checks from the repository root:

```bash
npm run lint --workspace=apps/web
npm run build --workspace=apps/web
```

At the Day 35 local delivery point, the backend suite has **215 passing tests**, API lint is clean, and the frontend production build generates **20 routes**. The GitHub CI workflow runs API lint, API tests, and web lint/build on `main`.

## Deployment

| Component | Service | URL |
|---|---|---|
| Web dashboard | Vercel | <https://voxflow-voice-agent.vercel.app> |
| API | Render | <https://voxflow-voice-agent.onrender.com> |
| Job health | Render | <https://voxflow-voice-agent.onrender.com/api/jobs/health?tenant_id=varun> |
| Analytics overview | Render | <https://voxflow-voice-agent.onrender.com/api/analytics/overview?tenant_id=varun&days=30> |
| Normalized provider callbacks | Render | `<POST /api/provider-callbacks/events>`; intentionally returns `503` until its normalized callback secret is configured. |
| Dial sandbox callbacks | Render | `<POST /api/provider-callbacks/dial/events>`; intentionally returns `503` while `DIAL_CALLBACK_ADAPTER_ENABLED=false`. |
| Pilot readiness | Temporary backend after provisioning | `GET /api/pilot-readiness/varun`; read-only scorecard, intentionally blocked until human-owned evidence exists. |

The frontend currently uses `NEXT_PUBLIC_API_URL=https://voxflow-voice-agent.onrender.com`. While the documented Render outage persists, `railway.json` permits a reversible GitHub/Docker temporary backend. Only after safe HTTPS health/API verification should `NEXT_PUBLIC_API_URL` be changed to that temporary origin. Analytics, callback evidence, Day 34 side-effect health, and Day 35 pilot readiness are read-only with respect to activation: no dashboard panel can create a dial or execute an integration. The backend must retain all staged worker controls and empty allow-lists until the separate human go/no-go approval.

## Documentation map

| Document | Use it for |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Current system and durable-dispatch design. |
| [PRD.md](PRD.md) | Product scope, user outcomes, and pilot boundary. |
| [PHASES.md](PHASES.md) | Day-by-day delivery record and next implementation phase. |
| [MEMORY.md](MEMORY.md) | Live project status and next operational action. |
| [schema.md](schema.md) | Schema reference, durable-job tables, and policy records. |
| [SETUP.md](SETUP.md) | Current Render/Vercel deployment and staging verification procedure. |
| [security_audit.md](security_audit.md) | Security controls, known gaps, and verification commands. |
| [.learning/README.md](.learning/README.md) | Local-only theory and implementation journal. |
| [.planning/planning_overview.md](.planning/planning_overview.md) | Current roadmap index and historical-plan boundary. |

## License

Distributed under the MIT License. See [LICENSE](LICENSE).
