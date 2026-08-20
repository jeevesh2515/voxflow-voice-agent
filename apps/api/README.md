# VoxFlow API

FastAPI backend for VoxFlow voice operations, tenant-scoped operational APIs, inbound telephony, and durable campaign execution.

## Current responsibilities

| Area | Implementation |
|---|---|
| Voice and operations API | Inbound voice/webhook/media-stream paths, dashboard APIs, operational tools, tenant-aware data access. |
| Durable jobs | Job ledger, transactional outbox, atomic claim/lease, retries, attempt history, stale-worker protection, graceful drain. |
| Campaign dispatch | Feature-gated worker handler, dry run, provider-operation idempotency, reconciliation/no-redial behavior. |
| Tenant safety | Job/campaign/policy reads scoped by tenant; explicit policy, consent, opt-out, quota, and capacity gate dispatch. |
| Auditability | Job attempts, provider operations, policy decisions, health/read models, and cancellation reason codes. |

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

At the Day 30 milestone, the full backend suite has **182 passing tests**.

## Durable campaign migration sequence

```text
003_durable_job_ledger.sql
004_outbox_relay_state.sql
005_campaign_policy_controls.sql
```

Use the migration files for production schema changes. Local test setup creates current SQLAlchemy metadata automatically.

## Campaign execution safety

The campaign worker is intentionally separated from FastAPI request handlers. Do not invoke a provider from an API request or start a worker against production credentials for local testing.

Production must retain:

```text
DURABLE_CAMPAIGN_WORKER_ENABLED=false
```

A future internal canary requires a tenant allow-list, valid tenant policy, consented test recipient, dry-run evidence, daily/in-flight limits of one, observability, and rollback ownership. The policy evaluator cancels missing consent/policy/opt-out/inactive campaign conditions before a `ProviderOperation` is reserved.

## Key paths

| Path | Purpose |
|---|---|
| `voxflow_api/db.py` | SQLAlchemy models and database setup. |
| `voxflow_api/jobs/` | Ledger, outbox, worker, provider operations, reconciliation, policy. |
| `voxflow_api/routes/campaigns.py` | Campaign command/read APIs and policy decision audit read. |
| `voxflow_api/routes/campaign_policies.py` | Tenant policy and recipient preference APIs. |
| `voxflow_api/routes/jobs.py` | Tenant-safe durable job health and recent-job read APIs. |
| `tests/` | Deterministic unit/API/integration coverage; providers are mocked. |

See the root [README](../../README.md), [architecture](../../ARCHITECTURE.md), [schema reference](../../schema.md), and [security audit](../../security_audit.md) for project-wide guidance.
