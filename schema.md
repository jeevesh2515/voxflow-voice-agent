# VoxFlow Database Schema Reference

**Last updated:** 2026-08-20
**Authoritative implementation:** `apps/api/voxflow_api/db.py` and the ordered SQL files in `migrations/`.
**Purpose of this document:** Explain tenant boundaries, durable execution, policy controls, Day 32 provider callback evidence, and Day 33 provider-adapter audit evidence. It is not a substitute for applying production migrations.

## 1. Schema and migration authority

Local SQLite development/tests create the SQLAlchemy metadata. Production PostgreSQL changes must be applied through the checked-in migration sequence. For durable campaign delivery, apply migrations in this order:

```text
003_durable_job_ledger.sql
004_outbox_relay_state.sql
005_campaign_policy_controls.sql
006_provider_callback_lifecycle.sql
007_dial_sandbox_callback_adapter.sql
```

The initial tenant/core schema and prior feature migrations must already be present. Do not copy partial DDL from this document into a production database; use the migration files so indexes and constraints remain aligned with code.

## 2. Tenant isolation model

Every operational, campaign, durable-job, provider-operation, and policy record is owned by `tenant_id` or is reached from a tenant-owned parent. API handlers filter by tenant. The dashboard passes the active tenant for campaign, queue, and health reads. PostgreSQL deployments must additionally enforce row-level security for tenant-scoped tables according to the production access model.

| Rule | Meaning |
|---|---|
| Tenant owns data | No campaign target, job, preference, audit decision, or provider operation may be queried/mutated across tenant boundaries. |
| Tenant derives from trusted context | API/session context or stored provider operation determines tenant identity; provider callback request fields are never trusted to select a tenant. |
| Tenant-safe reads | Job health, recent jobs, campaign queue, and policy-decision APIs return only the active/declared tenant’s data. |
| Append-only evidence | Job attempts and policy decisions preserve operational facts even after job/target state changes. |

## 3. Core operational tables

| Table | Tenant key | Role |
|---|---|---|
| `tenants` | Primary tenant record | Workspace/company identity and baseline ownership. |
| `suppliers` | `tenant_id` | Supplier/customer contacts, caller-verification metadata, and operational directory. |
| `products`, `stock` | `tenant_id` | Tenant product catalog and warehouse stock. |
| `orders`, `shipments` | `tenant_id` | Purchase-order and logistics workflow records. |
| `calls` | `tenant_id` | Voice transcript, outcome, verification, and resolution evidence. |
| `appointments` | `tenant_id` | Dock/meeting scheduling records. |
| `communication_logs` | `tenant_id` | Email/SMS/WhatsApp-related operational communication history. |
| `tenant_phone_numbers` | `tenant_id` | Inbound number-to-tenant mapping for telephony routing. |
| `outbound_campaigns` | `tenant_id` | Campaign configuration and aggregate target/call counters. |
| `campaign_queue` | `tenant_id` | Individual campaign targets, status, call ID, retry time, and transcript summary. |

## 4. Durable execution tables (Days 25–29)

| Table | Key columns and constraints | Purpose |
|---|---|---|
| `job_runs` | `id`, `tenant_id`, `job_type`, payload, status, priority, schedule/next-run, lease owner/expiry, attempt/max attempts, idempotency key, error fields | The durable unit of work. States include `ready`, `running`, `retry_scheduled`, `succeeded`, `cancelled`, and `dead_lettered`. |
| `job_outbox` | Tenant-owned event aggregate, payload, publish/lease state, idempotency key | Prevents loss between a committed domain change and job publication. |
| `job_attempts` | Job ID, worker, started/finished timestamps, outcome, error evidence | Immutable execution/claim history. `policy_deferred` is an intentional business wait, not an unclassified failure. |
| `provider_operations` | Tenant, provider, operation type, idempotency key, request hash, provider ID, durable status | Owns the external provider side-effect boundary. |
| `provider_events` | Tenant-derived operation reference, provider/event/call IDs, type, occurrence time, payload hash, redacted normalized facts, application/anomaly status | Immutable signed-callback history; unique `(provider, provider_event_id)` enforces delivery idempotency. |
| `provider_callback_quarantines` | Provider event/call metadata, payload hash, reason, timestamps; intentionally no tenant ID | Safe record for a trusted callback that cannot resolve an existing provider operation. |
| `provider_callback_adapter_audits` | Optional derived tenant, provider event ID/type, payload hash, verification/normalization/application dispositions, reason, timestamp; unique `(provider, provider_event_id, payload_hash)` | Redacted immutable receipt for the Day 33 provider-specific adapter. It records safe verification and rollout-gate outcomes without storing raw bodies, headers, signatures, secrets, phone numbers, or transcripts. |

The durable job repository uses conditional state transitions that verify the current `running` state, lease owner, and unexpired lease. This prevents a stale worker from completing, cancelling, or retrying a job it no longer owns.

## 5. Day 30 tenant policy tables

| Table | Key fields | Purpose |
|---|---|---|
| `tenant_campaign_policies` | `tenant_id`, `timezone_name`, `calling_window_start/end`, `daily_call_limit`, `max_in_flight`, `enabled` | Explicit tenant dispatch policy. A missing/disabled/invalid policy fails closed. |
| `recipient_campaign_preferences` | `(tenant_id, recipient_phone)` unique pair, consent status/purpose, opt-out, source | Current recipient permission state for outbound operational campaigns. |
| `tenant_daily_dispatch_usage` | `(tenant_id, local_date)` unique pair, reserved calls, active dispatches | Atomic tenant-local daily quota/capacity record. |
| `campaign_dispatch_reservations` | `job_id` unique, tenant, local date, `active/released/settled` state | One capacity reservation per dispatch job; prevents double consumption. |
| `campaign_policy_decisions` | Tenant, job, campaign, queue target, decision, reason code, evidence, next eligibility time | Append-only policy audit evidence. |

### Policy-linked statuses

| Layer | Status/outcome | Meaning |
|---|---|---|
| Job | `cancelled` | Terminal policy decision; not a retryable infrastructure failure. |
| Job attempt | `policy_deferred` | A deliberate wait until a policy-selected time. |
| Queue target | `cancelled` | The target must not reach a provider. |
| Reservation | `released` | No provider request was issued; budget and capacity were released. |
| Reservation | `settled` | Dry-run or terminal provider outcome completed; active capacity released while the day’s call decision remains accounted for. |
| Policy decision | `allowed`, `deferred`, `cancelled` | Immutable record of every dispatch-policy evaluation. |

## 6. Day 32 provider callback evidence

`provider_events.tenant_id` is derived only after the service resolves an existing `provider_operations` row by `(provider, provider_id)`. The callback transport never supplies an authoritative tenant, campaign, queue, or job reference. Unknown calls are inserted only into `provider_callback_quarantines`, which deliberately has no tenant relationship.

| Callback evidence field | Data handling rule |
|---|---|
| `provider_event_id` and `provider_call_id` | Used for idempotency and stored-operation lookup; not shown in the tenant analytics aggregate. |
| `payload_hash` | Retained for forensic equality checks; raw callback payload is not stored in the event ledger. |
| `normalized_payload_json` | Contains only normalized outcome facts needed for reconciliation. It must not contain secrets, transcript content, or raw provider payload. |
| `apply_status` and `anomaly_code` | Used for operator lifecycle aggregate and alerting; does not by itself authorize a retry or re-dial. |

A terminal callback may finalize the job associated with the durable provider operation even if that job is waiting in a callback-pending retry state. The transition is guarded by the stored operation identity, immutable event deduplication, and terminal-state checks; late callbacks cannot reopen a completed, cancelled, or dead-lettered job.

## 7. Day 33 adapter audit evidence

`provider_callback_adapter_audits` is intentionally distinct from `provider_events`. It contains one provider-adapter receipt per event/payload-hash identity, whereas `provider_events` exists only when the generic Day 32 lifecycle service receives a normalized observation. A valid Dial event can therefore be audited as `blocked_tenant`, `acknowledged`, or `rejected` without any campaign, queue, job, capacity, or provider-operation mutation.

| Field | Data-handling rule |
|---|---|
| `tenant_id` | Null until and unless the normalized callback resolves exactly one stored outbound operation. It is derived from storage, never callback input. |
| `verification_status` | `verified` or `rejected`; used for tenant-safe monitoring only where a tenant was safely derived. |
| `normalization_status` | `normalized`, `ignored`, `ping`, or `not_normalized`; never contains a raw provider payload. |
| `application_status` | `applied`, `duplicate`, `blocked_tenant`, `acknowledged`, `rejected`, or a Day 32 lifecycle disposition. |
| `payload_hash` | Cryptographic equality evidence only. It is not a recoverable callback body. |
| `reason_code` | Bounded operational code such as `invalid_dial_signature` or `dial_callback_tenant_not_allowed`; no raw exception detail. |

## 8. Relationship map

```mermaid
erDiagram
    TENANTS ||--o{ OUTBOUND_CAMPAIGNS : owns
    TENANTS ||--o{ CAMPAIGN_QUEUE : owns
    TENANTS ||--o{ JOB_RUNS : owns
    TENANTS ||--o{ PROVIDER_OPERATIONS : owns
    TENANTS ||--o{ PROVIDER_EVENTS : derived_ownership
    TENANTS ||--o{ PROVIDER_CALLBACK_ADAPTER_AUDITS : derived_when_known
    TENANTS ||--|| TENANT_CAMPAIGN_POLICIES : configures
    TENANTS ||--o{ RECIPIENT_CAMPAIGN_PREFERENCES : owns
    TENANTS ||--o{ TENANT_DAILY_DISPATCH_USAGE : tracks
    OUTBOUND_CAMPAIGNS ||--o{ CAMPAIGN_QUEUE : contains
    JOB_RUNS ||--o{ JOB_ATTEMPTS : records
    PROVIDER_OPERATIONS ||--o{ PROVIDER_EVENTS : receives
    JOB_RUNS ||--|| CAMPAIGN_DISPATCH_RESERVATIONS : reserves
    JOB_RUNS ||--o{ CAMPAIGN_POLICY_DECISIONS : explains
    CAMPAIGN_QUEUE ||--o{ CAMPAIGN_POLICY_DECISIONS : evaluated
```

## 9. Data-handling requirements

1. New operational tables must remain tenant scoped and have production migration coverage.
2. Tenant policy/audit endpoint responses must redact raw evidence data unless a scoped administrator workflow explicitly needs it.
3. The provider operation idempotency key must be stable for the job’s intended provider request.
4. Do not delete or overwrite attempt/policy evidence in normal execution paths.
5. Expensive or external work must occur after the durable state is committed and must reconcile back through tenant-owned records.
6. Provider callbacks must validate freshness and a provider-specific signature before they are normalized or persisted; a missing secret must fail closed.
7. Unknown provider IDs must quarantine without creating a tenant, campaign, queue, job, or provider operation.
8. Provider-adapter audit rows must persist only hashes, bounded event metadata, and bounded dispositions; never raw bodies, signature headers, secrets, phone numbers, or transcript content.
9. A provider-specific adapter must be explicitly enabled in sandbox mode, have a signing secret, and resolve an allow-listed stored-operation tenant before it may create a Day 32 lifecycle event.
10. Schema changes that affect policy, consent, jobs, provider operations, or provider events require migration review, targeted tests, and a `schema.md` update.

## References

- `apps/api/voxflow_api/db.py`
- `apps/api/voxflow_api/jobs/repository.py`
- `apps/api/voxflow_api/jobs/campaign_policy.py`
- `migrations/003_durable_job_ledger.sql`
- `migrations/004_outbox_relay_state.sql`
- `migrations/005_campaign_policy_controls.sql`
- `migrations/006_provider_callback_lifecycle.sql`
- `migrations/007_dial_sandbox_callback_adapter.sql`
