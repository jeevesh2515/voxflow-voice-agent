# VoxFlow API

FastAPI backend for VoxFlow voice operations, tenant-scoped operational APIs, inbound telephony, and durable campaign execution.

## Current responsibilities

| Area | Implementation |
|---|---|
| Voice and operations API | Inbound voice/webhook/media-stream paths, dashboard APIs, operational tools, tenant-aware data access. |
| Durable jobs | Job ledger, transactional outbox, atomic claim/lease, retries, attempt history, stale-worker protection, graceful drain, and typed redacted side-effect intents. |
| Campaign dispatch | Feature-gated worker handler, dry run, provider-operation idempotency, reconciliation/no-redial behavior. |
| Tenant safety | Job/campaign/policy reads scoped by tenant; explicit policy, consent, opt-out, quota, and capacity gate dispatch. |
| Auditability | Job attempts, provider operations, policy decisions, immutable provider events, quarantined unknown callbacks, redacted provider-adapter audit receipts, health/read models, and cancellation reason codes. |
| Provider callbacks | Fail-closed normalized ingress plus disabled-by-default Dial sandbox HMAC adapter, tenant-derived lookup, event deduplication, terminal reconciliation, rollout gate, and lifecycle aggregates. |
| Operational side effects | Separate Day 34 worker service for Sheets, email scans, CRM sync, notifications, worksheet writes, and recording retrieval; all request paths persist intent only. |

## Local run

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m voxflow_api.seed --reset
uvicorn voxflow_api.main:app --reload --port 8000
```

The default local database is SQLite. Production uses a PostgreSQL-compatible database and applies the migration sequence in `../../migrations/`.

## Quality checks

```bash
.venv/bin/ruff check voxflow_api tests
.venv/bin/pytest -q
```

At the Day 34 local milestone, the full backend suite has **204 passing tests** and API lint is clean.

## Durable campaign migration sequence

```text
003_durable_job_ledger.sql
004_outbox_relay_state.sql
005_campaign_policy_controls.sql
006_provider_callback_lifecycle.sql
007_dial_sandbox_callback_adapter.sql
008_typed_durable_side_effect_jobs.sql
```

Use the migration files for production schema changes. Local test setup creates current SQLAlchemy metadata automatically.

## Campaign execution safety

The campaign worker is intentionally separated from FastAPI request handlers. Do not invoke a provider from an API request or start a worker against production credentials for local testing.

Production must retain:

```text
DURABLE_CAMPAIGN_WORKER_ENABLED=false
PROVIDER_CALLBACK_VALIDATE_SIGNATURE=true
PROVIDER_CALLBACK_SHARED_SECRET=(intentionally unset)
DIAL_CALLBACK_ADAPTER_ENABLED=false
DIAL_CALLBACK_SANDBOX_MODE=true
DIAL_CALLBACK_ALLOWED_TENANTS=(intentionally empty)
DIAL_CALLBACK_SIGNING_SECRETS=(intentionally unset)
DURABLE_SIDE_EFFECTS_WORKER_ENABLED=false
DURABLE_SIDE_EFFECTS_DRY_RUN=true
DURABLE_SIDE_EFFECTS_ALLOWED_TENANTS=(intentionally empty)
```

A future internal canary requires a tenant allow-list, valid tenant policy, consented test recipient, dry-run evidence, daily/in-flight limits of one, observability, and rollback ownership. The policy evaluator cancels missing consent/policy/opt-out/inactive campaign conditions before a `ProviderOperation` is reserved.

`POST /api/provider-callbacks/events` accepts only a normalized callback for a **pre-existing** provider operation. When validation is enabled, it requires a fresh `X-VoxFlow-Timestamp` and HMAC `X-VoxFlow-Signature` over `timestamp + "." + raw_body`. An absent callback secret returns `503` before a database mutation. The callback never accepts a trusted tenant, campaign, queue, or job ID; it derives tenant ownership from the stored `(provider, provider_call_id)` operation.

Day 33 adds `POST /api/provider-callbacks/dial/events`. It rejects with `503` before parsing while `DIAL_CALLBACK_ADAPTER_ENABLED=false` (the production default). In sandbox-only fixture tests, it validates Dial’s raw-body `X-Dial-Signature`, enforces freshness and header/body event identity, maps only outbound `call.status_changed`/`call.ended` events to the neutral Day 32 lifecycle, and acknowledges a signed ping without a lifecycle event. A verified event still requires a stored-operation tenant in `DIAL_CALLBACK_ALLOWED_TENANTS`; otherwise it records a redacted `blocked_tenant` audit only. The endpoint never creates a subscription, fetches a provider secret, or sends a call.

Day 34 adds `SideEffectIntent` plus `enqueue_side_effect` / `enqueue_side_effect_async`. A trusted business or audit row, durable intent, `JobRun`, and `JobOutbox` commit together; the job payload exposes only an intent ID. `side_effect_worker_service.py` owns an explicit handler allow-list and builds only when its own global gate and tenant allow-list are present. FastAPI starts neither the old Sheets retry loop nor the email scan scheduler. In the deployed default, the worker is off; in future dry-run admission it records `dry_run` intent evidence and must not call Sheets, Gmail, CRM, Twilio, Dial, or recording endpoints. `POST /api/admin/email-summarizer/run` now queues an email scan job rather than fetching mail in an HTTP request.

## Key paths

| Path | Purpose |
|---|---|
| `voxflow_api/db.py` | SQLAlchemy models and database setup. |
| `voxflow_api/jobs/` | Ledger, outbox, worker, provider operations, reconciliation, policy, and typed side-effect intent services. |
| `voxflow_api/routes/campaigns.py` | Campaign command/read APIs and policy decision audit read. |
| `voxflow_api/routes/campaign_policies.py` | Tenant policy and recipient preference APIs. |
| `voxflow_api/routes/jobs.py` | Tenant-safe durable job health and recent-job read APIs. |
| `voxflow_api/routes/provider_callbacks.py` | Signature-verified normalized callback ingress. |
| `voxflow_api/routes/dial_callbacks.py` | Day 33 Dial sandbox ingress, fail-closed rollout gate, and Day 32 handoff. |
| `voxflow_api/integrations/dial_callbacks.py` | Dial signature parsing, HMAC/freshness verification, and outbound lifecycle normalizer. |
| `voxflow_api/jobs/provider_events.py` | Immutable event application, terminal guards, tenant-safe lookup, and quarantine. |
| `voxflow_api/jobs/provider_adapter_audits.py` | Redacted adapter verification/normalization/rollout audit receipts. |
| `voxflow_api/jobs/side_effects.py` | Typed side-effect constants and atomic sync/async intent/outbox enqueue helpers. |
| `voxflow_api/jobs/side_effect_worker_service.py` | Isolated staged worker and Sheets/email/CRM/notification/recording handlers. |
| `tests/test_side_effect_jobs.py` | Day 34 atomicity, idempotency, dry-run, retry, tenant isolation, and no-direct-call regression tests. |
| `tests/` | Deterministic unit/API/integration coverage; providers are mocked. |

See the root [README](../../README.md), [architecture](../../ARCHITECTURE.md), [schema reference](../../schema.md), and [security audit](../../security_audit.md) for project-wide guidance.
