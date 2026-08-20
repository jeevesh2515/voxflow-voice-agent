# VoxFlow Architecture

**Last updated:** 2026-08-20
**Current milestone:** Day 35 — controlled-pilot readiness complete in source; local tests and frontend build passed. Deployed verification is pending a staged temporary backend while Render’s free-service deployment incident persists.
**Operating mode:** Inbound voice and dashboard functions are deployed. Campaign dispatch and operational side-effect workers are independently safe-staged, and Day 35 pilot admission is fail-closed with an empty tenant allow-list.

## 1. System boundaries

VoxFlow separates the latency-sensitive inbound voice path from durable operational work. FastAPI receives web/API requests and persists intent. Durable workers claim lease-protected jobs from the database and execute bounded units of background work. Campaign provider calls are not performed inside the campaign HTTP request transaction.

```mermaid
flowchart TB
    Browser[Next.js dashboard\nVercel] --> API
    Twilio[Twilio inbound voice\nwebhook + media stream] --> API[FastAPI API and voice gateway\nRender]
    API --> Voice[Voice pipeline\nSTT → agent tools → TTS]
    API --> DB[(PostgreSQL production\nSQLite local tests)]
    API --> Outbox[JobOutbox]
    Outbox --> Ledger[JobRun + JobAttempt]
    Ledger --> Worker[Campaign WorkerRuntime\nindependent process]
    Worker --> Gate[Campaign policy gate]
    Gate --> Pilot[Day 35 pilot admission\nconfiguration + hashed cohort]
    Pilot --> Audit[CampaignPolicyDecision]
    Gate --> ProviderOp[ProviderOperation]
    Ledger --> SideWorker[Side-effect WorkerRuntime\nseparate gated process]
    SideWorker --> Intent[SideEffectIntent\ntrusted aggregate references]
    Intent --> Integrations[Sheets / CRM / notification / recording]
    ProviderOp --> Dial[Dial outbound client]
    Dial --> Callback[Dial sandbox adapter\nraw-body HMAC + normalizer + tenant gate]
    Callback --> Audit[Redacted adapter-audit ledger]
    Callback --> Events[Immutable ProviderEvent ledger]
    Events --> Recon[Idempotent reconciliation or quarantine]
    Recon --> DB
```

| Boundary | Owner | Rule |
|---|---|---|
| Inbound voice | FastAPI voice pipeline | Preserve per-call latency; never wait on campaign jobs or outbox relays. |
| Command/control plane | FastAPI routes | Validate and persist tenant-scoped intent; do not create an outbound provider side effect inline. |
| Durable execution | `WorkerRuntime` | Claim only leased jobs, use conditional transitions, retry only typed transient errors. |
| Provider side effect | `ProviderOperation` | One idempotency key owns one provider request; retries reconcile rather than re-dial. |
| Normalized provider callback | `provider_callbacks.py` + `provider_events.py` | Verify generic timestamp/signature, derive tenant from stored operation, deduplicate immutable events, and quarantine unknown IDs. |
| Dial sandbox callback | `dial_callbacks.py` + `integrations/dial_callbacks.py` | Fail closed unless sandbox adapter/secret/allow-list are explicit; verify Dial raw-body HMAC, normalize documented outbound call events, audit safely, then hand off to Day 32. |
| Campaign permission | `campaign_policy.py` + `pilot_readiness.py` | Fail closed before provider intent: policy, consent, opt-out, explicit pilot tenant/configuration/cohort/expiry/coverage, timing, budget, and capacity. |
| Operational side effects | `side_effects.py` + `side_effect_worker_service.py` | Persist intent/outbox with a trusted aggregate; execute only from a separate feature-gated, tenant-scoped worker. |
| Pilot readiness | `pilot_readiness.py` + read-only route | Freeze metric definitions, show redacted cohort/coverage/expiry/rollback evidence, and keep all approval/activation operations outside HTTP. |
| Operator visibility | Job health and analytics dashboard | Show tenant-owned counts and redacted audit/read models only; no activation control. |

## 2. Runtime components

### Frontend

`apps/web` is a Next.js 16.3.1 application deployed on Vercel. It uses TypeScript, Tailwind CSS, and SWR. The tenant context is passed to campaign lists, queue views, run/stage actions, health, and recent job reads. The campaigns page visualizes staged rollout state, durable job health, queued targets, and policy cancellations.

### FastAPI backend

`apps/api/voxflow_api` provides synchronous and asynchronous SQLAlchemy paths, inbound voice routes, dashboard APIs, campaign APIs, and job-health read models. The backend runs on Render in the deployed environment and supports SQLite for deterministic local tests.

### Durable job subsystem

The Day 25–34 subsystem lives in `apps/api/voxflow_api/jobs/`.

| Component | Responsibility |
|---|---|
| `enqueue.py` | Atomically persists campaign target intent and outbox event. |
| `outbox.py` | Leases and relays unprocessed transactional outbox events. |
| `repository.py` | Atomic claim, lease extension, success, retry, cancel, dead-letter, and recovery transitions. |
| `worker.py` | Bounded polling runtime, typed outcomes, backoff, graceful drain, and stale-worker protection. |
| `campaign_worker_service.py` | Standalone campaign worker entry point with global gate and canary tenant filter. |
| `campaign_dispatch.py` | Campaign target handler: policy, capacity, dry run, provider-operation reservation, and no-redial behavior. |
| `provider_operations.py` | Durable idempotency reservation and provider operation updates. |
| `reconciliation.py` | Applies provider terminal outcomes back to job/campaign state. |
| `provider_events.py` | Applies already-authenticated provider events, preserves event history, prevents terminal regression, and quarantines unknown provider call IDs. |
| `provider_adapter_audits.py` | Stores redacted, idempotent verification/normalization/rollout receipts for provider-specific adapters. |
| `campaign_policy.py` | Tenant policy evaluation, consent/opt-out enforcement, reservations, and immutable audit records. |
| `side_effects.py` | Typed effect constants plus sync/async transactional enqueue and redacted intent transitions. |
| `side_effect_worker_service.py` | Standalone Sheets/email/CRM/notification/recording handler registry with independent feature, tenant, and dry-run gates. |

## 3. Campaign dispatch lifecycle

```mermaid
sequenceDiagram
    participant UI as Dashboard/API
    participant DB as PostgreSQL
    participant W as WorkerRuntime
    participant P as Policy evaluator
    participant D as Provider adapter
    participant C as Signed callback ingress

    UI->>DB: enqueue target + outbox in one transaction
    DB-->>W: lease-protected JobRun claim
    W->>P: evaluate tenant policy and recipient permission
    alt cancelled
        P->>DB: CampaignPolicyDecision + queue/job cancelled
    else deferred
        P->>DB: CampaignPolicyDecision + exact next_run_at
    else allowed
        P->>DB: reserve daily budget and active capacity
        W->>DB: reserve ProviderOperation idempotency key
        alt dry run
            W->>DB: mark dry-run completion and settle capacity
        else live worker enabled
            W->>D: one provider request
            D-->>W: accepted / rejected
            W->>DB: persist operation result
            D-->>C: signed lifecycle callback
            C->>DB: immutable provider event or quarantine
            C->>DB: idempotent terminal reconciliation
        end
    end
```

A `requested` provider operation with unknown acceptance is retried through reconciliation, not by making a second provider request. An `accepted` operation waits for a callback/reconciliation terminal result. Terminal outcomes settle active capacity; a pre-request policy deferral or lease loss releases unused capacity and budget reservation.

## 4. Provider callback lifecycle

Day 32 exposes `POST /api/provider-callbacks/events`, a normalized callback ingress for an existing provider operation. With signature validation enabled, the route requires a current timestamp and HMAC-SHA256 signature over the raw body. The endpoint fails closed with `503` when no callback secret is configured, which is the deployed default until a provider-specific sandbox adapter is certified.

| Incoming condition | Durable response |
|---|---|
| Valid new event for known operation | Append `provider_events` record and apply only the allowed lifecycle transition. |
| Exact event replay | Return idempotent success with no new event, counter, job, or provider request. |
| Unknown call ID | Append `provider_callback_quarantines` record with no tenant mutation. |
| Late event after terminal operation | Retain a marked event but do not reopen queue/job/counters. |
| Terminal success/failure | Reconcile queue/campaign/capacity and terminal durable job once. |

Day 33 adds the Dial-specific adapter at `POST /api/provider-callbacks/dial/events`, but it is deployed in a certification-only posture. It parses `X-Dial-Signature: t=<unix-seconds>,v1=<hex-hmac>`, verifies HMAC-SHA256 over `timestamp + "." + raw body`, accepts only a configured current/previous secret overlap, and bounds replay age. It maps only documented outbound `call.status_changed` and `call.ended` events into the Day 32 neutral lifecycle; signed `webhook.ping` is acknowledged without creating a business event. The route cannot apply an event unless `DIAL_CALLBACK_ADAPTER_ENABLED=true`, sandbox mode remains true, a secret exists, and the resolved tenant is explicitly allow-listed. No raw provider callback payload, signature, secret, transcript, phone number, or job payload is rendered in analytics or stored in the adapter audit ledger. [1] [2] [3]

## 5. Operational side-effect lifecycle

Day 34 moves API-process Sheets retry, periodic email scheduling, direct agent notification delivery, fire-and-forget CRM posting, generic worksheet writes, and recording follow-up into the durable job contract. `SideEffectIntent` stores only a type, trusted aggregate reference, idempotency key, hash, and bounded result state. It never stores a raw external payload.

| Source path | Atomic write | Typed job | Worker-owned behavior |
|---|---|---|---|
| Call outcome | `WorksheetLog` + intent/outbox | `sheets.call_outcome.append` | Reads the stored canonical row and mirrors it only after approval. |
| Email summary | `CommunicationLog` + `WorksheetLog` + intent/outbox | `email.summarization.scan`, `sheets.email_summary.append` | Fetches/summarizes only in the worker and mirrors stored summary rows. |
| CRM event | Order, appointment, or worksheet escalation/outcome + intent/outbox | `crm.webhook.sync` | Derives event payload from the trusted aggregate. |
| Notification | `CommunicationLog(status=queued)` + intent/outbox | `notification.dispatch` | Reads a stored communication record; voice/API code never calls Twilio inline. |
| Recording callback | `Call.recording_url` + intent/outbox | `recording.retrieve` | Performs no media request until a future separately approved non-dry-run storage design exists. |

The worker builds only if `DURABLE_SIDE_EFFECTS_WORKER_ENABLED=true` **and** an explicit tenant allow-list exists. In Day 34 production defaults it is disabled. If it is later admitted in dry-run, a claimed intent receives a bounded `dry_run` result and no integration client is invoked. Retryable transport faults retain `retry_scheduled`; malformed aggregate, missing configuration, or unsupported channels retain bounded terminal evidence. The existing `WorkerRuntime` owns lease renewal, retries, stale-worker recovery, and attempt history.

## 6. Tenant policy and auditable cancellation

The policy gate runs before `ProviderOperation` reservation. A dispatch target must satisfy all conditions below.

| Check | Data source | Failed outcome |
|---|---|---|
| Tenant policy exists and is enabled | `tenant_campaign_policies` | `tenant_policy_missing` or `tenant_policy_disabled` cancellation |
| Campaign is active/running | `outbound_campaigns` | `campaign_not_active` cancellation |
| Consent is granted | `recipient_campaign_preferences` | `consent_not_granted` cancellation |
| Recipient is not opted out | `recipient_campaign_preferences` | `recipient_opted_out` cancellation |
| Consent purpose covers dispatch | Recipient preference + campaign type | `consent_purpose_mismatch` cancellation |
| Calling window is open in tenant timezone | Tenant policy | `outside_calling_window` exact deferral |
| Daily budget remains | `tenant_daily_dispatch_usage` | `daily_call_budget_exhausted` deferral |
| Active tenant capacity remains | Same usage record | `tenant_concurrency_limited` deferral |
| Pilot tenant explicitly approved | `PILOT_READINESS_APPROVED_TENANTS` | `pilot_tenant_not_approved` cancellation |
| Written pilot is approved/unexpired/staffed/micro-capped | `pilot_configurations` | Pilot configuration/expiry/coverage/capacity cancellation |
| Recipient belongs to reviewed fixed cohort | `pilot_cohort_members` SHA-256 hash | `pilot_cohort_mismatch` cancellation |

Every policy evaluation appends a `campaign_policy_decisions` record.
 The operator endpoint returns decision, reason code, timestamp, and next eligible time, but does not expose raw evidence JSON. Policy cancellations map to terminal durable `cancelled` jobs rather than dead letters.

## 7. Data model

The core business schema remains tenant scoped. Durable dispatch adds the following tables.

| Table | Purpose |
|---|---|
| `job_runs` | Durable queued work, state, lease, retry timing, idempotency key, and terminal outcome. |
| `job_outbox` | Transactional events persisted with domain changes and published by a relay. |
| `job_attempts` | Immutable execution-attempt evidence. |
| `provider_operations` | Provider-side idempotency and reconciliation boundary. |
| `provider_events` | Append-only signed callback evidence with provider-event idempotency and application/anomaly state. |
| `provider_callback_quarantines` | Trusted-but-unmatched callback evidence that deliberately has no tenant link. |
| `provider_callback_adapter_audits` | Redacted immutable Dial-adapter verification, normalization, and tenant-rollout receipts. |
| `tenant_campaign_policies` | Tenant timezone, calling window, quota, capacity, and enablement. |
| `recipient_campaign_preferences` | Consent, purpose, opt-out, and provenance per tenant/phone. |
| `tenant_daily_dispatch_usage` | Tenant-local daily reservation and active-dispatch counters. |
| `campaign_dispatch_reservations` | One capacity reservation per job with active/released/settled lifecycle. |
| `campaign_policy_decisions` | Immutable Day 30 policy audit evidence. |
| `side_effect_intents` | Day 34 append-only tenant effect owner with a one-to-one durable job, aggregate reference, idempotency key, hash, redacted result, and status. |
| `pilot_configurations` | Versioned one-tenant readiness contract: cohort reference/count, IANA window, micro-capacity, expiry, named coverage, approver, and metric contract. |
| `pilot_cohort_members` | Reviewed cohort membership represented only by tenant-scoped SHA-256 recipient hashes and consent-evidence references. |
| `pilot_security_incidents` | Bounded confirmed security findings that make the pilot’s zero-incident objective measurable rather than assumed. |

Production migrations are ordered as `003_durable_job_ledger.sql`, `004_outbox_relay_state.sql`, `005_campaign_policy_controls.sql`, `006_provider_callback_lifecycle.sql`, `007_dial_sandbox_callback_adapter.sql`, `008_typed_durable_side_effect_jobs.sql`, then `009_controlled_pilot_readiness.sql`.

## 8. Production safety and rollout

The deployed backend remains in a non-executing campaign posture:

```text
DURABLE_CAMPAIGN_WORKER_ENABLED=false
PILOT_READINESS_ENFORCED=true
PILOT_READINESS_APPROVED_TENANTS=(intentionally empty)
PROVIDER_CALLBACK_VALIDATE_SIGNATURE=true
PROVIDER_CALLBACK_SHARED_SECRET=(intentionally unset)
DIAL_CALLBACK_ADAPTER_ENABLED=false
DIAL_CALLBACK_SANDBOX_MODE=true
DIAL_CALLBACK_ALLOWED_TENANTS=(intentionally empty)
DIAL_CALLBACK_SIGNING_SECRETS=(intentionally unset)
DURABLE_SIDE_EFFECTS_WORKER_ENABLED=false
DURABLE_SIDE_EFFECTS_DRY_RUN=true
DURABLE_SIDE_EFFECTS_ALLOWED_TENANTS=(intentionally empty)
activation_mode=staged
canary_allowed=false
dry_run=true
```

These settings are a deliberate layered control, not a missing feature. An internal canary must use a dedicated worker process, explicit tenant allow-list, dry-run evidence, tenant policy configuration, consented test target, concurrency one, monitoring, and a rollback owner. The dashboard’s `Launch Campaign` control does not bypass the worker gate or invoke the provider inline.

## 9. Engineering quality gates

| Surface | Command |
|---|---|
| Backend lint | `cd apps/api && .venv/bin/ruff check voxflow_api tests` |
| Backend tests | `cd apps/api && .venv/bin/pytest -q` |
| Frontend lint | `npm run lint --workspace=apps/web` |
| Frontend production build | `npm run build --workspace=apps/web` |
| Live job posture | `GET /api/jobs/health?tenant_id=varun` |

At the Day 35 local delivery point, the backend suite has **215 passing tests**, API lint is clean, and the frontend production build generates 20 routes. GitHub CI validates API lint, API test, and web lint/build on every `main` delivery.

## References

- `apps/api/voxflow_api/jobs/`
- `apps/api/voxflow_api/db.py`
- `migrations/003_durable_job_ledger.sql`
- `migrations/004_outbox_relay_state.sql`
- `migrations/005_campaign_policy_controls.sql`
- `migrations/006_provider_callback_lifecycle.sql`
- `migrations/007_dial_sandbox_callback_adapter.sql`
- `migrations/008_typed_durable_side_effect_jobs.sql`
- `migrations/009_controlled_pilot_readiness.sql`
- `apps/api/voxflow_api/pilot_readiness.py`
- `apps/api/voxflow_api/routes/pilot_readiness.py`
- `railway.json`
- `apps/api/voxflow_api/jobs/side_effects.py`
- `apps/api/voxflow_api/jobs/side_effect_worker_service.py`
- `apps/api/voxflow_api/integrations/dial_callbacks.py`
- `apps/api/voxflow_api/routes/dial_callbacks.py`
- `apps/web/src/app/dashboard/analytics/page.tsx`

[1] [Dial Webhooks](https://docs.getdial.ai/documentation/platform/webhooks.md)
[2] [Dial `call.status_changed`](https://docs.getdial.ai/api-reference/events/call-status-changed.md)
[3] [Dial `call.ended`](https://docs.getdial.ai/api-reference/events/call-ended.md)
